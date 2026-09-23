"""Triage: score findings, correlate with activity, and drive the pipeline.

Severity alone is a poor queue. Ten CRITICALs tell you nothing about which one
to open first. This module scores each finding on four axes that actually change
the answer:

  exposure      is it reachable by an unauthenticated party
  blast radius  what does an attacker get if they use it
  recoverability can the damage be undone
  activity      has anything actually touched this resource recently

The activity signal comes from CloudTrail, so a public bucket nobody has touched
ranks below a public bucket that is being read right now. That is the difference
between a compliance report and an incident queue.

Entry point for the whole agent:

    python3 -m src.triage                  scan, score, and show the plan
    python3 -m src.triage --apply          run the auto-remediations (dry-run)
    python3 -m src.triage --apply --live   actually change things
    python3 -m src.triage --approve ID     also run one approval-gated fix
    python3 -m src.triage --json           machine-readable output
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from botocore.exceptions import ClientError

from . import aws_client, remediate
from .classifier import Finding, Severity, scan_all

log = logging.getLogger(__name__)

ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"

# Rules whose finding means an unauthenticated party can reach the resource.
_PUBLIC_RULES = {"S3_PUBLIC_BUCKET_POLICY", "SQS_PUBLIC_QUEUE_POLICY"}
# Rules that hand over control of the account rather than one resource.
_ADMIN_RULES = {"IAM_INLINE_ADMIN", "IAM_ATTACHED_ADMIN"}
# Rules whose damage cannot be undone once exploited.
_IRRECOVERABLE_RULES = {"IAM_INLINE_ADMIN", "IAM_ATTACHED_ADMIN", "S3_NO_VERSIONING"}


@dataclass
class Triaged:
    finding: Finding
    score: int
    factors: dict[str, int]
    rationale: str
    recent_events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.finding.to_dict(),
            "risk_score": self.score,
            "factors": self.factors,
            "rationale": self.rationale,
            "recent_event_count": len(self.recent_events),
        }


# ------------------------------------------------------------- correlation --
def recent_activity(resource_id: str, hours: int = 24, limit: int = 5) -> list[dict[str, Any]]:
    """CloudTrail events mentioning this resource.

    Best-effort: CloudTrail lookup is rate-limited in real AWS and only partially
    implemented in emulators, so a failure here degrades the score rather than
    breaking the run.
    """
    try:
        ct = aws_client.cloudtrail()
        resp = ct.lookup_events(
            LookupAttributes=[{"AttributeKey": "ResourceName", "AttributeValue": resource_id}],
            StartTime=datetime.now(timezone.utc) - timedelta(hours=hours),
            MaxResults=limit,
        )
    except (ClientError, Exception) as exc:  # noqa: BLE001 - deliberately broad
        log.debug("cloudtrail lookup failed for %s: %s", resource_id, exc)
        return []

    return [
        {"event": e.get("EventName"), "user": e.get("Username"),
         "time": str(e.get("EventTime"))}
        for e in resp.get("Events", [])
    ]


# ------------------------------------------------------------------ scoring --
def score_finding(f: Finding, events: list[dict[str, Any]] | None = None) -> Triaged:
    events = events or []
    factors: dict[str, int] = {}

    # Base weight from severity: 15 / 30 / 45 / 60.
    factors["severity"] = int(f.severity) * 15

    if f.rule_id in _PUBLIC_RULES:
        factors["internet_exposed"] = 20
    if f.rule_id in _ADMIN_RULES:
        factors["account_takeover"] = 20
    if f.rule_id in _IRRECOVERABLE_RULES:
        factors["irrecoverable"] = 5
    if events:
        factors["recent_activity"] = min(10, 2 * len(events))
    if not f.auto_remediable:
        factors["no_auto_fix"] = 5

    score = min(100, sum(factors.values()))

    bits = []
    if "internet_exposed" in factors:
        bits.append("reachable without credentials")
    if "account_takeover" in factors:
        bits.append("grants full account control")
    if "irrecoverable" in factors:
        bits.append("damage would be hard to undo")
    if events:
        bits.append(f"{len(events)} CloudTrail event(s) in the last 24h")
    if not f.auto_remediable:
        bits.append("no automated fix available")
    rationale = f"{f.severity.label}" + (": " + "; ".join(bits) if bits else "")

    return Triaged(finding=f, score=score, factors=factors,
                   rationale=rationale, recent_events=events)


def triage(findings: Iterable[Finding], correlate: bool = True) -> list[Triaged]:
    out: list[Triaged] = []
    for f in findings:
        events = recent_activity(f.resource_id) if correlate else []
        out.append(score_finding(f, events))
    out.sort(key=lambda t: (-t.score, -int(t.finding.severity), t.finding.resource_id))
    return out


# ------------------------------------------------------- optional AI layer --
def narrative(triaged: list[Triaged]) -> str:
    """A short written summary of the estate.

    Deterministic by default. If ANTHROPIC_API_KEY is set and the `anthropic`
    package is installed, the same input is sent to a model for a richer
    write-up. The pipeline never depends on that being available -- an agent
    that stops working when an API key expires is not a security control.
    """
    if not triaged:
        return "No findings. Nothing in the estate matched any rule."

    crit = [t for t in triaged if t.finding.severity is Severity.CRITICAL]
    public = [t for t in triaged if t.finding.rule_id in _PUBLIC_RULES]
    admin = [t for t in triaged if t.finding.rule_id in _ADMIN_RULES]

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _llm_narrative(triaged)
        except Exception as exc:  # noqa: BLE001
            log.warning("LLM summary unavailable (%s); using deterministic summary", exc)

    lines = [f"{len(triaged)} finding(s) across the estate, "
             f"{len(crit)} critical."]
    if public:
        names = ", ".join(sorted({t.finding.resource_id for t in public}))
        lines.append(f"Reachable without credentials: {names}. Fix these first — "
                     f"exposure is live whether or not anyone has noticed yet.")
    if admin:
        names = ", ".join(sorted({t.finding.resource_id for t in admin}))
        lines.append(f"Full account control granted to: {names}. Each of these is a single "
                     f"compromise away from total account takeover.")
    top = triaged[0]
    lines.append(f"Highest scored: {top.finding.rule_id} on {top.finding.resource_id} "
                 f"({top.score}/100) — {top.rationale}.")
    return " ".join(lines)


def _llm_narrative(triaged: list[Triaged]) -> str:
    import anthropic  # imported lazily; optional dependency

    payload = [t.to_dict() for t in triaged[:15]]
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=400,
        system=("You are a cloud security engineer writing the summary paragraph of a "
                "findings report. Be specific and plain. Name resources. Say what an "
                "attacker gets. No preamble, no bullet points, under 150 words."),
        messages=[{"role": "user", "content": json.dumps(payload, default=str)}],
    )
    return msg.content[0].text.strip()


# -------------------------------------------------------------------- report --
def write_report(triaged: list[Triaged], decisions: list[remediate.Decision]) -> Path:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS / f"report-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.json"
    path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "endpoint": aws_client.get_endpoint_url(),
        "summary": remediate.summarise(decisions),
        "narrative": narrative(triaged),
        "findings": [t.to_dict() for t in triaged],
        "decisions": [d.to_dict() for d in decisions],
    }, indent=2, default=str))
    return path


def _print_table(triaged: list[Triaged], decisions: list[remediate.Decision]) -> None:
    by_id = {d.finding_id: d for d in decisions}
    print(f"\n{'SCORE':>5}  {'SEVERITY':<9} {'RULE':<30} {'RESOURCE':<28} PLAN")
    print("-" * 96)
    for t in triaged:
        d = by_id.get(t.finding.id)
        verdict = d.verdict.value if d else "-"
        print(f"{t.score:>5}  {t.finding.severity.label:<9} {t.finding.rule_id:<30} "
              f"{t.finding.resource_id:<28} {verdict}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Scan, triage, and remediate the local Floci estate.")
    ap.add_argument("--apply", action="store_true", help="run remediations (dry-run unless --live)")
    ap.add_argument("--live", action="store_true", help="actually change resources")
    ap.add_argument("--approve", action="append", default=[], metavar="FINDING_ID",
                    help="approve one approval-gated finding; repeatable")
    ap.add_argument("--no-correlate", action="store_true", help="skip CloudTrail lookups")
    ap.add_argument("--min-severity", choices=[s.name for s in Severity], default="HIGH",
                    help="threshold for automatic remediation (default HIGH)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")

    health = aws_client.health()
    if not health["reachable"]:
        print(f"Cannot reach the emulator at {health['endpoint']}: {health.get('error')}")
        print("Is the Floci container running?  docker ps")
        return 1

    findings = scan_all()
    triaged = triage(findings, correlate=not args.no_correlate)

    policy = remediate.Policy(min_severity=Severity[args.min_severity])
    decisions = remediate.plan([t.finding for t in triaged], policy)

    if args.apply:
        decisions = remediate.execute(decisions, policy,
                                      dry_run=not args.live, approve=args.approve)

    report = write_report(triaged, decisions)

    if args.json:
        print(report.read_text())
        return 0

    print(f"\nEndpoint : {health['endpoint']}  (account {health.get('account')})")
    print(f"Findings : {len(findings)}")
    _print_table(triaged, decisions)

    print("\nSummary:", json.dumps(remediate.summarise(decisions)))
    print("\n" + narrative(triaged))

    gated = [d for d in decisions if d.verdict is remediate.Verdict.APPROVAL]
    if gated and not args.approve:
        print("\nNeeds approval (re-run with --approve <id>):")
        for d in gated:
            print(f"  {d.finding_id}\n      {d.reason}")

    if args.apply and not args.live:
        print("\nDry run. Nothing was changed. Add --live to apply.")

    print(f"\nReport: {report.relative_to(Path.cwd()) if report.is_relative_to(Path.cwd()) else report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
