# Lab 01 — Terraform tasks

You write the resources. The requirements are in comments inside each `.tf`
file; this is the order and the acceptance criteria.

```bash
cd projects/01-cost-visibility
./scripts/check.sh          # progress, formatting, validation, requirement checks
```

Nothing here touches Azure. `terraform validate` is offline.

---

## Order

| # | File | Resource | Why it's here |
|---|---|---|---|
| 1.1 | `main.tf` | Resource group | Warm-up |
| 1.2 | `main.tf` | Log Analytics workspace | Destination for diagnostic logs |
| 1.3 | `main.tf` | User-assigned identity | The thing that reads cost data |
| 1.4 | `main.tf` | Role assignment | Least privilege in practice |
| 1.5 | `main.tf` | Storage account | The security baseline task |
| 1.6 | `main.tf` | Storage container | Where exports land |
| 1.7 | `main.tf` | Diagnostic setting | Who read the cost data |
| 2.1 | `monitoring.tf` | Action group | Alert delivery (needs a `dynamic` block) |
| 2.2 | `monitoring.tf` | Cost anomaly alert | Catches spikes a budget misses |
| 3.1 | `budget.tf` | Subscription budget | The centrepiece — four notifications |
| 4.1 | `export.tf` | Cost management export | Daily CSV of real usage |
| 5.1 | `outputs.tf` | Outputs | So you stop hunting in the portal |

Do 1.1 and 1.2 first and run `check.sh`. Getting the loop working matters more
than getting far.

---

## Rules

**Use the registry docs, not memory.**
<https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs> — search
the resource name. Finding arguments in provider docs is the skill being built.

**Read errors before asking.** Terraform errors name the file, line, and usually
the exact argument. Every error you work through is content for `LAB-LOG.md`.

**Ask me for a hint, not the answer.** I have a reference implementation. If you
want it, say so and it's yours — but ask for a nudge first. The reason for
choosing this path was being able to explain the code later.

**Write down decisions as you make them.** Every task comment with a "think
about" question is an interview question in disguise. Answer it in
`DECISIONS.md` while the reasoning is fresh.

---

## Known traps

These are the ones that will actually bite. Not telling you the answers.

- **1.4** — a user-assigned identity exposes both `principal_id` and
  `client_id`. Only one is the right input for a role assignment.
- **1.5** — the HTTPS-only argument was renamed in azurerm v4. The v3 name
  produces a clear error. Read it.
- **1.6** — in v4 this takes the storage account by ID, not by name.
- **1.7** — the target is the blob *service*, not the account. And use
  `enabled_metric`; `metric` is deprecated and goes away in v5.
- **2.1** — `var.alert_emails` is a list. One hardcoded block is wrong.
- **3.1** — the subscription argument wants a full resource ID, not a GUID.
- **4.1** — needs an explicit `depends_on`. Work out why Terraform can't
  infer it.

---

## Done means

`./scripts/check.sh` shows zero TODOs, validation passing, and every
requirement check `[ok]`. Then Step 1 of `OUTLINE.md`: plan, screenshot,
apply, screenshot.
