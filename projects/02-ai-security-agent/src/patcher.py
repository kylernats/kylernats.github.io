"""Low-level remediation primitives.

One function per fix. Each one:

  1. snapshots the current state before touching anything,
  2. applies the change through the real boto3 API,
  3. verifies the change actually took effect,
  4. returns a structured result including how to undo it.

The snapshot matters more than it looks. Automated remediation that cannot be
reversed is worse than no remediation, because the first time it makes a wrong
call in a real account nobody will ever trust it again. Every action here writes
its prior state to `artifacts/backups/` and can be rolled back from that file.

`remediate.py` decides *whether* to run these. This module only knows *how*.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from botocore.exceptions import ClientError

from . import aws_client

log = logging.getLogger(__name__)

BACKUP_DIR = Path(__file__).resolve().parent.parent / "artifacts" / "backups"

SAFE_PUBLIC_ACCESS_BLOCK = {
    "BlockPublicAcls": True,
    "IgnorePublicAcls": True,
    "BlockPublicPolicy": True,
    "RestrictPublicBuckets": True,
}


@dataclass
class PatchResult:
    action: str
    target: str
    applied: bool
    dry_run: bool
    summary: str
    before: Any = None
    after: Any = None
    backup_file: str | None = None
    verified: bool | None = None
    error: str | None = None
    at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PatchError(RuntimeError):
    pass


# ------------------------------------------------------------------- backups --
def _save_backup(action: str, target: str, state: Any) -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    safe = target.replace("/", "_").replace(":", "_")
    path = BACKUP_DIR / f"{stamp}-{action}-{safe}.json"
    path.write_text(json.dumps(
        {"action": action, "target": target,
         "captured_at": datetime.now(timezone.utc).isoformat(), "state": state},
        indent=2, default=str))
    return str(path)


# ------------------------------------------------------------------ S3 fixes --
def s3_remove_public_policy(bucket: str, dry_run: bool = True) -> PatchResult:
    """Strip statements that grant access to Principal '*'.

    Deletes the policy outright when every statement was public, otherwise
    rewrites it keeping the legitimate statements. Blanket-deleting a policy
    that also carried real grants would cause an outage, which is the kind of
    "fix" that gets automation switched off.
    """
    s3 = aws_client.s3()
    from .classifier import _as_list, _has_wildcard_principal, _policy_doc

    try:
        current = _policy_doc(s3.get_bucket_policy(Bucket=bucket)["Policy"])
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "NoSuchBucketPolicy":
            return PatchResult("s3_remove_public_policy", bucket, False, dry_run,
                               "No bucket policy present; nothing to do.")
        raise

    statements = _as_list(current.get("Statement"))
    keep = [s for s in statements if not _has_wildcard_principal(s)]
    removed = len(statements) - len(keep)

    if removed == 0:
        return PatchResult("s3_remove_public_policy", bucket, False, dry_run,
                           "Policy has no public statements.", before=current)

    summary = (f"Remove {removed} public statement(s); "
               f"{'delete policy entirely' if not keep else f'keep {len(keep)}'}.")
    if dry_run:
        return PatchResult("s3_remove_public_policy", bucket, False, True,
                           f"[dry-run] {summary}", before=current)

    backup = _save_backup("s3_remove_public_policy", bucket, current)
    if keep:
        new_doc = {**current, "Statement": keep}
        s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps(new_doc))
    else:
        s3.delete_bucket_policy(Bucket=bucket)
        new_doc = None

    # verify
    try:
        after = _policy_doc(s3.get_bucket_policy(Bucket=bucket)["Policy"])
        verified = not any(_has_wildcard_principal(s) for s in _as_list(after.get("Statement")))
    except ClientError:
        after, verified = None, True

    return PatchResult("s3_remove_public_policy", bucket, True, False, summary,
                       before=current, after=after, backup_file=backup, verified=verified)


def s3_enable_public_access_block(bucket: str, dry_run: bool = True) -> PatchResult:
    s3 = aws_client.s3()
    try:
        before = s3.get_public_access_block(Bucket=bucket)["PublicAccessBlockConfiguration"]
    except ClientError:
        before = None

    summary = "Enable all four public access block settings."
    if dry_run:
        return PatchResult("s3_enable_public_access_block", bucket, False, True,
                           f"[dry-run] {summary}", before=before)

    backup = _save_backup("s3_enable_public_access_block", bucket, before)
    s3.put_public_access_block(Bucket=bucket,
                               PublicAccessBlockConfiguration=SAFE_PUBLIC_ACCESS_BLOCK)
    after = s3.get_public_access_block(Bucket=bucket)["PublicAccessBlockConfiguration"]
    verified = all(after.get(k) for k in SAFE_PUBLIC_ACCESS_BLOCK)

    return PatchResult("s3_enable_public_access_block", bucket, True, False, summary,
                       before=before, after=after, backup_file=backup, verified=verified)


def s3_enable_versioning(bucket: str, dry_run: bool = True) -> PatchResult:
    s3 = aws_client.s3()
    before = s3.get_bucket_versioning(Bucket=bucket).get("Status")
    summary = "Enable bucket versioning."
    if dry_run:
        return PatchResult("s3_enable_versioning", bucket, False, True,
                           f"[dry-run] {summary}", before=before)

    backup = _save_backup("s3_enable_versioning", bucket, {"Status": before})
    s3.put_bucket_versioning(Bucket=bucket, VersioningConfiguration={"Status": "Enabled"})
    after = s3.get_bucket_versioning(Bucket=bucket).get("Status")

    return PatchResult("s3_enable_versioning", bucket, True, False, summary,
                       before=before, after=after, backup_file=backup,
                       verified=after == "Enabled")


# ----------------------------------------------------------------- IAM fixes --
def iam_delete_inline_policy(role: str, policy_name: str, dry_run: bool = True) -> PatchResult:
    """Remove an over-permissive inline policy from a role.

    The full document is saved first. Deleting an inline policy is destructive
    and there is no AWS-side recycle bin for it.
    """
    iam = aws_client.iam()
    target = f"{role}/{policy_name}"
    try:
        before = iam.get_role_policy(RoleName=role, PolicyName=policy_name).get("PolicyDocument")
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "NoSuchEntity":
            return PatchResult("iam_delete_inline_policy", target, False, dry_run,
                               "Inline policy no longer present.")
        raise

    summary = f"Delete inline policy '{policy_name}' from role '{role}'."
    if dry_run:
        return PatchResult("iam_delete_inline_policy", target, False, True,
                           f"[dry-run] {summary}", before=before)

    backup = _save_backup("iam_delete_inline_policy", target, before)
    iam.delete_role_policy(RoleName=role, PolicyName=policy_name)

    remaining = iam.list_role_policies(RoleName=role).get("PolicyNames", [])
    return PatchResult("iam_delete_inline_policy", target, True, False, summary,
                       before=before, after={"remaining_inline_policies": remaining},
                       backup_file=backup, verified=policy_name not in remaining)


def iam_detach_policy(role: str, policy_arn: str, dry_run: bool = True) -> PatchResult:
    """Detach an over-permissive managed policy. The policy itself is left intact."""
    iam = aws_client.iam()
    target = f"{role}/{policy_arn.rsplit('/', 1)[-1]}"
    before = {"role": role, "policy_arn": policy_arn}

    summary = f"Detach {policy_arn} from role '{role}'."
    if dry_run:
        return PatchResult("iam_detach_policy", target, False, True,
                           f"[dry-run] {summary}", before=before)

    backup = _save_backup("iam_detach_policy", target, before)
    iam.detach_role_policy(RoleName=role, PolicyArn=policy_arn)

    still = [a["PolicyArn"] for a in
             iam.list_attached_role_policies(RoleName=role).get("AttachedPolicies", [])]
    return PatchResult("iam_detach_policy", target, True, False, summary,
                       before=before, after={"attached_policies": still},
                       backup_file=backup, verified=policy_arn not in still)


# ----------------------------------------------------------------- SQS fixes --
def sqs_remove_public_policy(queue_url: str, dry_run: bool = True) -> PatchResult:
    sqs = aws_client.sqs()
    from .classifier import _as_list, _has_wildcard_principal, _policy_doc

    name = queue_url.rsplit("/", 1)[-1]
    attrs = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["Policy"]).get("Attributes", {})
    current = _policy_doc(attrs.get("Policy"))
    if not current:
        return PatchResult("sqs_remove_public_policy", name, False, dry_run,
                           "No queue policy present.")

    statements = _as_list(current.get("Statement"))
    keep = [s for s in statements if not _has_wildcard_principal(s)]
    removed = len(statements) - len(keep)
    if removed == 0:
        return PatchResult("sqs_remove_public_policy", name, False, dry_run,
                           "Queue policy has no public statements.", before=current)

    summary = f"Remove {removed} public statement(s) from queue policy."
    if dry_run:
        return PatchResult("sqs_remove_public_policy", name, False, True,
                           f"[dry-run] {summary}", before=current)

    backup = _save_backup("sqs_remove_public_policy", name, current)
    # An empty string clears the policy; SQS rejects a policy with no statements.
    new_policy = json.dumps({**current, "Statement": keep}) if keep else ""
    sqs.set_queue_attributes(QueueUrl=queue_url, Attributes={"Policy": new_policy})

    after_raw = sqs.get_queue_attributes(
        QueueUrl=queue_url, AttributeNames=["Policy"]).get("Attributes", {}).get("Policy")
    after = _policy_doc(after_raw)
    verified = not any(_has_wildcard_principal(s) for s in _as_list(after.get("Statement")))

    return PatchResult("sqs_remove_public_policy", name, True, False, summary,
                       before=current, after=after or None, backup_file=backup, verified=verified)


# ---------------------------------------------------------------- dispatch ---
ACTIONS: dict[str, Callable[..., PatchResult]] = {
    "s3_remove_public_policy": s3_remove_public_policy,
    "s3_enable_public_access_block": s3_enable_public_access_block,
    "s3_enable_versioning": s3_enable_versioning,
    "iam_delete_inline_policy": iam_delete_inline_policy,
    "iam_detach_policy": iam_detach_policy,
    "sqs_remove_public_policy": sqs_remove_public_policy,
}

# Actions that destroy state a human may not be able to reconstruct. The
# orchestrator refuses to run these unattended.
DESTRUCTIVE = {"iam_delete_inline_policy", "iam_detach_policy"}


def apply(spec: dict[str, Any], dry_run: bool = True) -> PatchResult:
    """Run one remediation from a finding's `remediation` dict."""
    params = dict(spec)
    action = params.pop("action", None)
    if action not in ACTIONS:
        raise PatchError(f"Unknown remediation action: {action!r}")
    return ACTIONS[action](**params, dry_run=dry_run)


def rollback(backup_file: str) -> PatchResult:
    """Restore state captured by a previous patch."""
    data = json.loads(Path(backup_file).read_text())
    action, target, state = data["action"], data["target"], data["state"]

    if action == "s3_remove_public_policy":
        aws_client.s3().put_bucket_policy(Bucket=target, Policy=json.dumps(state))
    elif action == "s3_enable_public_access_block":
        if state:
            aws_client.s3().put_public_access_block(
                Bucket=target, PublicAccessBlockConfiguration=state)
        else:
            aws_client.s3().delete_public_access_block(Bucket=target)
    elif action == "s3_enable_versioning":
        status = (state or {}).get("Status") or "Suspended"
        aws_client.s3().put_bucket_versioning(
            Bucket=target, VersioningConfiguration={"Status": status})
    elif action == "iam_delete_inline_policy":
        role, pname = target.split("/", 1)
        aws_client.iam().put_role_policy(RoleName=role, PolicyName=pname,
                                         PolicyDocument=json.dumps(state))
    elif action == "iam_detach_policy":
        aws_client.iam().attach_role_policy(RoleName=state["role"], PolicyArn=state["policy_arn"])
    elif action == "sqs_remove_public_policy":
        url = aws_client.sqs().get_queue_url(QueueName=target)["QueueUrl"]
        aws_client.sqs().set_queue_attributes(QueueUrl=url, Attributes={"Policy": json.dumps(state)})
    else:
        raise PatchError(f"No rollback defined for action {action!r}")

    return PatchResult(f"rollback:{action}", target, True, False,
                       f"Restored state from {Path(backup_file).name}", after=state)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    print("Available remediation actions:")
    for name in sorted(ACTIONS):
        flag = "  (destructive, needs approval)" if name in DESTRUCTIVE else ""
        print(f"  {name}{flag}")
