# Cloud Drift Detection & Auto-Remediation Agent

Detects insecure AWS configuration, scores it by real risk rather than raw
severity, and fixes what it is safe to fix — against a local
[Floci](https://floci.dev) emulator, so it costs nothing and touches no real
account.

```
scripts/seed_floci.py   →   classifier.py   →   triage.py   →   remediate.py   →   patcher.py
  create the mess           find it            rank it         decide             fix it
```

## Run it

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt

./.venv/bin/python scripts/seed_floci.py      # create misconfigured resources
./.venv/bin/python -m src.triage              # scan, score, show the plan (changes nothing)
./.venv/bin/python -m src.triage --apply      # dry-run the fixes
DRY_RUN=0 ./.venv/bin/python -m src.triage --apply --live   # actually fix
```

Approval-gated fixes need the finding id:

```bash
./.venv/bin/python -m src.triage --apply --live \
  --approve "IAM_INLINE_ADMIN:agentlab-ci-deploy-role"
```

Useful extras: `--json`, `--min-severity MEDIUM`, `--no-correlate`,
`scripts/seed_floci.py --show`, `scripts/seed_floci.py --reset`.

## The modules

| File | Job |
|---|---|
| `src/aws_client.py` | One boto3 factory for the whole project. Pins the endpoint, injects dummy credentials, and **refuses to build a client for anything that is not localhost**. |
| `src/classifier.py` | Eight detection rules across S3, IAM, SQS, CloudTrail. Every field on a finding comes from a live API response, and the raw response is kept as evidence. |
| `src/triage.py` | Scores each finding 0–100 on exposure, blast radius, recoverability, and recent CloudTrail activity. Also the CLI entry point. |
| `src/remediate.py` | Decides whether a fix may run: AUTO, APPROVAL, or SKIP. Writes an append-only audit log. |
| `src/patcher.py` | Executes the fixes. Snapshots prior state, verifies the change landed, supports rollback. |
| `scripts/seed_floci.py` | Creates the misconfigured estate, plus correctly-configured control resources. |

## Design decisions worth defending

**The client factory refuses non-local endpoints.** This tool detaches IAM
policies and deletes bucket policies. The worst thing it could do is run against
a real account by accident, so that path is closed in code rather than mentioned
in a comment. Override needs an explicit `ALLOW_NON_LOCAL_ENDPOINT=1`.

**Dry-run is the default.** Applying requires both `--live` and `DRY_RUN=0`.

**Every change is snapshotted before it happens.** `artifacts/backups/` holds the
prior state and `patcher.rollback()` restores it. Automated remediation that
cannot be undone gets switched off the first time it makes a wrong call.

**Destructive fixes are gated on a specific finding id.** Deleting an inline IAM
policy cannot be reversed from AWS, so a human approves that one change rather
than flipping a blanket `--yes`.

**A protected list exists.** The agent will not modify the CloudTrail logging
bucket. An agent that can disable your audit trail is a liability, not a control.

**Public policy statements are stripped, not blanket-deleted.** If a bucket
policy mixes a public grant with legitimate ones, the legitimate statements are
kept. A "fix" that causes an outage teaches people to disable the tool.

**Severity is not the queue order.** Ten CRITICALs tell you nothing about what to
open first. Scoring adds internet exposure, account-takeover potential, whether
damage is recoverable, and whether CloudTrail shows anyone actually touching the
resource in the last 24 hours.

**Control resources are seeded deliberately.** `agentlab-locked-archive` and
`agentlab-readonly-role` are configured correctly. A detector that flags
everything is as useless as one that flags nothing, and these are what prove the
rules discriminate.

## Detection rules

| Rule | Severity | Auto-fix |
|---|---|---|
| `S3_PUBLIC_BUCKET_POLICY` | CRITICAL | yes |
| `IAM_INLINE_ADMIN` | CRITICAL | approval |
| `IAM_ATTACHED_ADMIN` | CRITICAL | approval |
| `S3_NO_PUBLIC_ACCESS_BLOCK` | HIGH | yes |
| `SQS_PUBLIC_QUEUE_POLICY` | HIGH | yes |
| `CLOUDTRAIL_NOT_MULTI_REGION` | MEDIUM | no |
| `IAM_INLINE_WILDCARD_ACTION` | MEDIUM | no — correct scope is a human decision |
| `S3_NO_CMK_ENCRYPTION` | LOW | no — choosing the key is a human decision |
| `S3_NO_VERSIONING` | LOW | yes |

## Emulator fidelity notes

Worth knowing before trusting a result from here in a real account.

- **Floci returns `AES256` default encryption for every bucket**, including one
  never configured. A "no encryption" rule can therefore never fire. Real AWS has
  also applied SSE-S3 by default since January 2023, so the rule that still
  discriminates is `aws:kms` versus `AES256` — which is what is implemented.
- **CloudTrail `lookup_events` returns little or nothing** on the emulator, so the
  activity factor in scoring is usually 0 locally. The code path is exercised but
  the signal is weak; against real CloudTrail it carries more weight.
- Correlation failures degrade the score rather than failing the run.

## Optional LLM summary

`triage.narrative()` is deterministic by default. If `ANTHROPIC_API_KEY` is set
and the `anthropic` package is installed, the same findings are sent to a model
for a richer written summary. The pipeline never depends on it — an agent that
stops working when an API key expires is not a security control.

## Output

- `artifacts/report-*.json` — findings, scores, decisions, narrative
- `artifacts/audit.jsonl` — append-only record of every decision and execution
- `artifacts/backups/*.json` — prior state for every change, used by rollback
