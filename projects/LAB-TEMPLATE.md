# Lab run sheet template

Reused for projects 02–05 so every lab produces the same evidence set.

## Screenshot points — every lab gets these seven

| Phase | Slug | Why it matters |
|---|---|---|
| **Baseline** | `baseline-*` | The "before". Impossible to retake later. Proves nothing was pre-built. |
| **Plan** | `terraform-plan` | Shows the change was reviewed before it was made. |
| **Apply** | `terraform-apply` | Proof of a real deployment, with outputs. |
| **Controls** | `control-*` | One shot per security control, showing it enabled in the portal. |
| **Control tested** | `*-denied` / `*-allowed` | The differentiator. Proves the control *works*, not just that it exists. |
| **Working system** | `*-rendered`, `*-email`, `*-data` | The thing doing its job for a human. |
| **Teardown** | `destroy`, `final-cost` | Cost discipline. The step most portfolios skip. |

## The rule

Configuring a control is not evidence. **Every lab must include at least one
screenshot of the control refusing to do something it should refuse to do.**

A screenshot of a settings page proves you clicked a toggle. A screenshot of an
`AuthorizationFailed` error proves you understand what the toggle does.

## Capture

```bash
./scripts/capture.sh <slug> "caption"   # files the newest Desktop screenshot
./scripts/snapshot.sh <label>           # dumps Azure API state as evidence
```

## Per-lab documents

- `docs/steps/OUTLINE.md` — the run sheet, written before the work starts
- `docs/LAB-LOG.md` — what happened, including errors, written as it happens
- `docs/DECISIONS.md` — decisions, alternatives, and the reasoning
- `docs/evidence/screenshots/` — images plus `INDEX.md` captions
- `docs/evidence/state/` — timestamped Azure API output
