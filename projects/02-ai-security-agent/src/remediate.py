"""Remediation orchestration and policy.

`patcher.py` knows how to make a change. This module decides whether it should,
which is the part that determines if anyone will let the tool run unattended.

The decision model is deliberately conservative:

  AUTO       - reversible, low blast radius, above the severity threshold
  APPROVAL   - destructive or high blast radius; a human confirms
  SKIP       - below threshold, no known fix, or explicitly protected

Everything is dry-run unless DRY_RUN=0 is set, and every decision and execution
is written to an append-only audit log. A remediation tool with no audit trail
is indistinguishable from an attacker.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from . import patcher
from .classifier import Finding, Severity

log = logging.getLogger(__name__)

AUDIT_DIR = Path(__file__).resolve().parent.parent / "artifacts"
AUDIT_LOG = AUDIT_DIR / "audit.jsonl"


class Verdict(str, Enum):
    AUTO = "auto"
    APPROVAL = "approval_required"
    SKIP = "skip"


@dataclass
class Policy:
    """What the agent is allowed to do without being asked."""

    # Nothing below this severity is touched automatically.
    min_severity: Severity = Severity.HIGH

    # Actions the agent may run unattended. Anything absent needs approval.
    auto_actions: frozenset[str] = frozenset({
        "s3_enable_public_access_block",
        "s3_remove_public_policy",
        "s3_enable_versioning",
        "sqs_remove_public_policy",
    })

    # Resources the agent must never modify, whatever the finding says. In a
    # real account this is where break-glass roles and the logging bucket go:
    # an agent that can disable your audit trail is a liability, not a control.
    protected: frozenset[str] = frozenset({
        "agentlab-trail-logs",
    })

    require_approval_for_destructive: bool = True

    def dry_run_default(self) -> bool:
        return os.environ.get("DRY_RUN", "1") != "0"


@dataclass
class Decision:
    finding_id: str
    rule_id: str
    resource_id: str
    severity: str
    verdict: Verdict
    reason: str
    action: str | None = None
    spec: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["verdict"] = self.verdict.value
        return d


# -------------------------------------------------------------------- audit --
def _audit(event: str, payload: dict[str, Any]) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    record = {"at": datetime.now(timezone.utc).isoformat(), "event": event, **payload}
    with AUDIT_LOG.open("a") as fh:
        fh.write(json.dumps(record, default=str) + "\n")


def read_audit(limit: int = 20) -> list[dict[str, Any]]:
    if not AUDIT_LOG.is_file():
        return []
    lines = AUDIT_LOG.read_text().strip().splitlines()
    return [json.loads(l) for l in lines[-limit:]]


# --------------------------------------------------------------------- plan --
def plan(findings: Iterable[Finding], policy: Policy | None = None) -> list[Decision]:
    """Turn findings into decisions without changing anything."""
    policy = policy or Policy()
    decisions: list[Decision] = []

    for f in findings:
        base = {
            "finding_id": f.id, "rule_id": f.rule_id,
            "resource_id": f.resource_id, "severity": f.severity.label,
        }

        if f.resource_id in policy.protected:
            decisions.append(Decision(**base, verdict=Verdict.SKIP,
                                      reason="Resource is on the protected list."))
            continue

        if f.remediation is None:
            decisions.append(Decision(**base, verdict=Verdict.SKIP,
                                      reason="No automated fix exists; needs a human decision."))
            continue

        action = f.remediation.get("action")

        if f.severity < policy.min_severity:
            decisions.append(Decision(**base, verdict=Verdict.SKIP, action=action,
                                      spec=f.remediation,
                                      reason=f"Severity below the {policy.min_severity.label} "
                                             f"threshold for automatic action."))
            continue

        if policy.require_approval_for_destructive and action in patcher.DESTRUCTIVE:
            decisions.append(Decision(**base, verdict=Verdict.APPROVAL, action=action,
                                      spec=f.remediation,
                                      reason="Destructive change; deleted IAM state cannot be "
                                             "reconstructed from AWS."))
            continue

        if action not in policy.auto_actions:
            decisions.append(Decision(**base, verdict=Verdict.APPROVAL, action=action,
                                      spec=f.remediation,
                                      reason="Action is not on the unattended allowlist."))
            continue

        decisions.append(Decision(**base, verdict=Verdict.AUTO, action=action,
                                  spec=f.remediation,
                                  reason="Reversible fix, above threshold, on the allowlist."))

    _audit("plan", {"decisions": [d.to_dict() for d in decisions]})
    return decisions


# ------------------------------------------------------------------ execute --
def execute(decisions: Iterable[Decision],
            policy: Policy | None = None,
            dry_run: bool | None = None,
            approve: Iterable[str] | None = None) -> list[Decision]:
    """Run the AUTO decisions, plus any APPROVAL ones explicitly approved.

    `approve` takes finding ids. Approving by id rather than a blanket flag means
    a human has looked at the specific change, which is the point of the gate.
    """
    policy = policy or Policy()
    dry_run = policy.dry_run_default() if dry_run is None else dry_run
    approved = set(approve or ())

    if not dry_run:
        log.warning("LIVE MODE: changes will be applied to %s",
                    os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566"))

    for d in decisions:
        runnable = d.verdict is Verdict.AUTO or (
            d.verdict is Verdict.APPROVAL and d.finding_id in approved)
        if not runnable or not d.spec:
            continue

        try:
            result = patcher.apply(d.spec, dry_run=dry_run)
            d.result = result.to_dict()
            level = logging.INFO if result.applied or dry_run else logging.WARNING
            log.log(level, "%-32s %s", d.resource_id, result.summary)
            if result.applied and result.verified is False:
                log.error("  change did not verify for %s", d.resource_id)
        except Exception as exc:
            d.result = {"error": f"{type(exc).__name__}: {exc}", "applied": False}
            log.error("%-32s FAILED: %s", d.resource_id, exc)

        _audit("execute", {"finding_id": d.finding_id, "dry_run": dry_run,
                           "result": d.result})

    return list(decisions)


def summarise(decisions: Iterable[Decision]) -> dict[str, Any]:
    ds = list(decisions)
    applied = [d for d in ds if (d.result or {}).get("applied")]
    failed = [d for d in ds if (d.result or {}).get("error")]
    return {
        "total": len(ds),
        "auto": sum(1 for d in ds if d.verdict is Verdict.AUTO),
        "approval_required": sum(1 for d in ds if d.verdict is Verdict.APPROVAL),
        "skipped": sum(1 for d in ds if d.verdict is Verdict.SKIP),
        "applied": len(applied),
        "failed": len(failed),
    }


if __name__ == "__main__":
    from .classifier import scan_all

    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    decisions = plan(scan_all())
    for d in decisions:
        print(f"  {d.verdict.value:<18} {d.severity:<9} {d.rule_id:<28} {d.resource_id}")
    print("\n", json.dumps(summarise(decisions), indent=2))
