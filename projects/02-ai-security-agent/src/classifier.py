"""Inspection and classification.

Queries the live Floci estate through boto3 and turns what it finds into
structured `Finding` objects. No mock files, no fixtures — every field on a
finding comes from an API response, and the raw response fragment is kept in
`evidence` so a human can check the call rather than trust the verdict.

Each rule states what it looks for and what an attacker does with it. A rule
that cannot answer "so what" is noise, and noise is what makes people stop
reading security tooling.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Iterable
from urllib.parse import unquote

from botocore.exceptions import ClientError

from . import aws_client

log = logging.getLogger(__name__)


class Severity(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    @property
    def label(self) -> str:
        return self.name


@dataclass
class Finding:
    rule_id: str
    severity: Severity
    resource_type: str
    resource_id: str
    title: str
    detail: str
    impact: str
    evidence: dict[str, Any] = field(default_factory=dict)
    remediation: dict[str, Any] | None = None   # action + args for the patcher
    arn: str | None = None
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def id(self) -> str:
        return f"{self.rule_id}:{self.resource_id}"

    @property
    def auto_remediable(self) -> bool:
        return self.remediation is not None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.label
        d["id"] = self.id
        d["auto_remediable"] = self.auto_remediable
        return d


# ------------------------------------------------------------------ helpers --
def _as_list(v: Any) -> list[Any]:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _policy_doc(raw: Any) -> dict[str, Any]:
    """Policy documents come back as a JSON string, a URL-encoded string, or a dict."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text.startswith("{"):
            text = unquote(text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}
    return {}


def _has_wildcard_principal(stmt: dict[str, Any]) -> bool:
    """True when a statement grants access to anyone at all."""
    if stmt.get("Effect") != "Allow":
        return False
    p = stmt.get("Principal")
    if p == "*":
        return True
    if isinstance(p, dict):
        for key in ("AWS", "Service", "*"):
            if "*" in _as_list(p.get(key)):
                return True
    return False


def _is_admin_statement(stmt: dict[str, Any]) -> bool:
    """True for Allow on Action:* over Resource:* — full account takeover."""
    if stmt.get("Effect") != "Allow":
        return False
    actions = [str(a) for a in _as_list(stmt.get("Action"))]
    resources = [str(r) for r in _as_list(stmt.get("Resource"))]
    return any(a == "*" for a in actions) and any(r == "*" for r in resources)


def _wildcard_actions(stmt: dict[str, Any]) -> list[str]:
    if stmt.get("Effect") != "Allow":
        return []
    return [str(a) for a in _as_list(stmt.get("Action")) if str(a).endswith(":*") or a == "*"]


# ------------------------------------------------------------------ S3 rules --
def scan_s3(only: Iterable[str] | None = None) -> list[Finding]:
    s3 = aws_client.s3()
    findings: list[Finding] = []

    buckets = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
    if only:
        wanted = set(only)
        buckets = [b for b in buckets if b in wanted]

    for name in buckets:
        arn = f"arn:aws:s3:::{name}"

        # --- publicly readable via bucket policy ---
        try:
            raw = s3.get_bucket_policy(Bucket=name)["Policy"]
            doc = _policy_doc(raw)
            public = [s for s in _as_list(doc.get("Statement")) if _has_wildcard_principal(s)]
            if public:
                findings.append(Finding(
                    rule_id="S3_PUBLIC_BUCKET_POLICY",
                    severity=Severity.CRITICAL,
                    resource_type="s3:bucket", resource_id=name, arn=arn,
                    title="Bucket policy grants access to any principal",
                    detail=(f"{len(public)} statement(s) allow access with Principal '*'. "
                            f"Actions: {sorted({a for s in public for a in _as_list(s.get('Action'))})}"),
                    impact="Anyone on the internet can read these objects without credentials. "
                           "This is the single most common cause of large data exposure incidents.",
                    evidence={"policy": doc, "public_statements": public},
                    remediation={"action": "s3_remove_public_policy", "bucket": name},
                ))
        except ClientError as exc:
            if exc.response["Error"]["Code"] not in ("NoSuchBucketPolicy", "NoSuchBucket"):
                log.debug("policy check failed for %s: %s", name, exc)

        # --- public access block missing or partial ---
        try:
            cfg = s3.get_public_access_block(Bucket=name)["PublicAccessBlockConfiguration"]
        except ClientError:
            cfg = {}
        required = ["BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets"]
        missing = [k for k in required if not cfg.get(k)]
        if missing:
            findings.append(Finding(
                rule_id="S3_NO_PUBLIC_ACCESS_BLOCK",
                severity=Severity.HIGH,
                resource_type="s3:bucket", resource_id=name, arn=arn,
                title="Public access block incomplete",
                detail=f"Not enabled: {', '.join(missing)}.",
                impact="Without this, one careless ACL or policy change makes the bucket "
                       "public. It is the backstop that stops a mistake becoming a breach.",
                evidence={"public_access_block": cfg or None, "missing": missing},
                remediation={"action": "s3_enable_public_access_block", "bucket": name},
            ))

        # --- encryption strength ---
        #
        # Checking for *absent* encryption is obsolete: AWS has applied SSE-S3 by
        # default since January 2023, and Floci mirrors that by returning AES256
        # for every bucket. So the rule that still discriminates is whether the
        # bucket uses a customer-managed KMS key rather than the S3-managed one.
        try:
            rules = s3.get_bucket_encryption(Bucket=name)[
                "ServerSideEncryptionConfiguration"].get("Rules", [])
        except ClientError:
            rules = []
        algos = [r.get("ApplyServerSideEncryptionByDefault", {}).get("SSEAlgorithm")
                 for r in rules]
        if rules and not any(a == "aws:kms" for a in algos):
            findings.append(Finding(
                rule_id="S3_NO_CMK_ENCRYPTION",
                severity=Severity.LOW,
                resource_type="s3:bucket", resource_id=name, arn=arn,
                title="Encrypted with S3-managed keys rather than a customer-managed key",
                detail=f"SSE algorithm in use: {algos or 'none'}.",
                impact="SSE-S3 protects the data at rest but AWS holds the key, so there is no "
                       "key policy to restrict who can decrypt and no independent audit trail of "
                       "key use. For regulated data a customer-managed KMS key is the expectation.",
                evidence={"rules": rules},
                remediation=None,   # choosing or creating the CMK is a human decision
            ))

        # --- versioning ---
        try:
            status = s3.get_bucket_versioning(Bucket=name).get("Status")
        except ClientError:
            status = None
        if status != "Enabled":
            findings.append(Finding(
                rule_id="S3_NO_VERSIONING",
                severity=Severity.LOW,
                resource_type="s3:bucket", resource_id=name, arn=arn,
                title="Versioning not enabled",
                detail=f"Versioning status: {status or 'never configured'}.",
                impact="An overwrite is unrecoverable. Ransomware encrypts by overwriting, "
                       "so versioning is what makes that reversible.",
                evidence={"versioning": status},
                remediation={"action": "s3_enable_versioning", "bucket": name},
            ))

    return findings


# ----------------------------------------------------------------- IAM rules --
def scan_iam(only: Iterable[str] | None = None) -> list[Finding]:
    iam = aws_client.iam()
    findings: list[Finding] = []

    roles = [r["RoleName"] for r in iam.list_roles().get("Roles", [])]
    if only:
        wanted = set(only)
        roles = [r for r in roles if r in wanted]

    for role in roles:
        # --- inline policies ---
        try:
            names = iam.list_role_policies(RoleName=role).get("PolicyNames", [])
        except ClientError:
            names = []
        for pname in names:
            doc = _policy_doc(iam.get_role_policy(RoleName=role, PolicyName=pname).get("PolicyDocument"))
            admin = [s for s in _as_list(doc.get("Statement")) if _is_admin_statement(s)]
            if admin:
                findings.append(Finding(
                    rule_id="IAM_INLINE_ADMIN",
                    severity=Severity.CRITICAL,
                    resource_type="iam:role", resource_id=role,
                    arn=f"arn:aws:iam::{aws_client.account_id()}:role/{role}",
                    title=f"Inline policy '{pname}' grants Action:* on Resource:*",
                    detail="An inline policy on this role permits every action on every resource.",
                    impact="Anything that assumes this role owns the account. Inline policies are "
                           "also easy to miss, because they do not appear in a list of managed policies.",
                    evidence={"policy_name": pname, "document": doc, "statements": admin},
                    remediation={"action": "iam_delete_inline_policy",
                                 "role": role, "policy_name": pname},
                ))
            else:
                wide = [a for s in _as_list(doc.get("Statement")) for a in _wildcard_actions(s)]
                if wide:
                    findings.append(Finding(
                        rule_id="IAM_INLINE_WILDCARD_ACTION",
                        severity=Severity.MEDIUM,
                        resource_type="iam:role", resource_id=role,
                        title=f"Inline policy '{pname}' uses wildcard actions",
                        detail=f"Wildcard actions granted: {sorted(set(wide))}.",
                        impact="Service-wide wildcards grant far more than the role usually needs, "
                               "which widens what an attacker can do after a compromise.",
                        evidence={"policy_name": pname, "wildcard_actions": sorted(set(wide))},
                        remediation=None,   # needs a human to decide the correct scope
                    ))

        # --- attached managed policies ---
        try:
            attached = iam.list_attached_role_policies(RoleName=role).get("AttachedPolicies", [])
        except ClientError:
            attached = []
        for att in attached:
            arn = att["PolicyArn"]
            doc = {}
            try:
                version = iam.get_policy(PolicyArn=arn)["Policy"]["DefaultVersionId"]
                doc = _policy_doc(iam.get_policy_version(
                    PolicyArn=arn, VersionId=version)["PolicyVersion"]["Document"])
            except ClientError as exc:
                log.debug("could not read managed policy %s: %s", arn, exc)

            admin = [s for s in _as_list(doc.get("Statement")) if _is_admin_statement(s)]
            if admin or arn.endswith(":policy/AdministratorAccess"):
                findings.append(Finding(
                    rule_id="IAM_ATTACHED_ADMIN",
                    severity=Severity.CRITICAL,
                    resource_type="iam:role", resource_id=role,
                    arn=f"arn:aws:iam::{aws_client.account_id()}:role/{role}",
                    title=f"Managed policy '{att['PolicyName']}' grants full administrative access",
                    detail=f"{arn} allows Action:* on Resource:* and is attached to this role.",
                    impact="Same blast radius as an inline admin policy: total account control "
                           "for anything able to assume the role.",
                    evidence={"policy_arn": arn, "document": doc, "statements": admin},
                    remediation={"action": "iam_detach_policy", "role": role, "policy_arn": arn},
                ))

    return findings


# ----------------------------------------------------------------- SQS rules --
def scan_sqs() -> list[Finding]:
    sqs = aws_client.sqs()
    findings: list[Finding] = []

    for url in sqs.list_queues().get("QueueUrls", []) or []:
        name = url.rsplit("/", 1)[-1]
        try:
            attrs = sqs.get_queue_attributes(
                QueueUrl=url, AttributeNames=["Policy", "QueueArn", "KmsMasterKeyId"]
            ).get("Attributes", {})
        except ClientError:
            continue

        doc = _policy_doc(attrs.get("Policy"))
        public = [s for s in _as_list(doc.get("Statement")) if _has_wildcard_principal(s)]
        if public:
            findings.append(Finding(
                rule_id="SQS_PUBLIC_QUEUE_POLICY",
                severity=Severity.HIGH,
                resource_type="sqs:queue", resource_id=name,
                arn=attrs.get("QueueArn"),
                title="Queue policy grants access to any principal",
                detail=f"{len(public)} statement(s) allow Principal '*'.",
                impact="Anyone can send messages into the queue, or read and delete them. "
                       "If a downstream consumer trusts these messages, that is remote input "
                       "into your processing pipeline.",
                evidence={"policy": doc, "public_statements": public, "queue_url": url},
                remediation={"action": "sqs_remove_public_policy", "queue_url": url},
            ))

    return findings


# ---------------------------------------------------------- CloudTrail rules --
def scan_cloudtrail() -> list[Finding]:
    ct = aws_client.cloudtrail()
    findings: list[Finding] = []

    try:
        trails = ct.describe_trails().get("trailList", [])
    except ClientError as exc:
        log.debug("describe_trails failed: %s", exc)
        return findings

    if not trails:
        findings.append(Finding(
            rule_id="CLOUDTRAIL_NO_TRAIL",
            severity=Severity.HIGH,
            resource_type="cloudtrail", resource_id="account",
            title="No CloudTrail trail configured",
            detail="Nothing is recording API activity in this account.",
            impact="After an incident there is no way to answer what happened, who did it, "
                   "or when it started. Detection and forensics both become guesswork.",
            evidence={"trails": []},
            remediation=None,
        ))
        return findings

    for t in trails:
        name = t.get("Name", "unknown")
        if not t.get("IsMultiRegionTrail"):
            findings.append(Finding(
                rule_id="CLOUDTRAIL_NOT_MULTI_REGION",
                severity=Severity.MEDIUM,
                resource_type="cloudtrail:trail", resource_id=name,
                arn=t.get("TrailARN"),
                title="Trail is single-region",
                detail=f"Trail '{name}' only records activity in {t.get('HomeRegion')}.",
                impact="Activity in any other region is invisible. Attackers routinely operate "
                       "in unused regions precisely because nobody is looking there.",
                evidence={"trail": {k: t.get(k) for k in ("Name", "HomeRegion", "IsMultiRegionTrail")}},
                remediation=None,
            ))

    return findings


# -------------------------------------------------------------------- driver --
def scan_all() -> list[Finding]:
    """Run every scanner. Individual failures do not abort the sweep."""
    findings: list[Finding] = []
    for name, fn in (("s3", scan_s3), ("iam", scan_iam),
                     ("sqs", scan_sqs), ("cloudtrail", scan_cloudtrail)):
        try:
            got = fn()
            log.info("scanned %-11s %d finding(s)", name, len(got))
            findings.extend(got)
        except Exception as exc:
            log.error("scanner %s failed: %s: %s", name, type(exc).__name__, exc)
    findings.sort(key=lambda f: (-f.severity, f.resource_type, f.resource_id))
    return findings


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    results = scan_all()
    print(json.dumps([f.to_dict() for f in results], indent=2, default=str))
    print(f"\n{len(results)} finding(s)")
