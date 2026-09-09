# Lab 01 — Cost Visibility Dashboard: run sheet

Kyler runs every step. Screenshots marked **📸** are the ones that end up in the
case study — take them at that exact moment, because most cannot be recreated
after the next step runs.

After each screenshot:

```bash
./scripts/capture.sh <slug> "one line describing what it shows"
```

That files it as `NN-slug.png` and writes the caption to the evidence index.
After each step, run `./scripts/snapshot.sh <label>` to capture machine-readable
proof from the Azure API.

---

## Step 0 — Baseline (before anything exists)

The "before" shots. These are impossible to retake once resources exist.

| 📸 | Where | What it must show |
|---|---|---|
| `00-baseline-empty-rg` | Portal → Resource groups | Only `NetworkWatcherRG`. Proves nothing was pre-built. |
| `01-baseline-credit` | Portal → Subscriptions → your sub → Overview | The $200 credit remaining and spend at $0 |
| `02-baseline-cost-analysis` | Cost Management → Cost analysis | Empty/near-zero chart for the current month |

```bash
./scripts/snapshot.sh baseline
```

---

## Step 1 — Read the code, then apply it

**Before running anything:** read every `.tf` file. You will be asked in an
interview why a specific value is set. Anything that does not make sense, ask
me now, not later.

| 📸 | Where | What it must show |
|---|---|---|
| `03-terraform-plan` | Terminal | `Plan: 14 to add, 0 to change, 0 to destroy` |
| `04-terraform-apply` | Terminal | `Apply complete! Resources: 14 added` plus the outputs block |

```bash
cd projects/01-cost-visibility/terraform
terraform plan -out=tfplan     # 📸 03
terraform apply tfplan         # 📸 04
cd ..
./scripts/snapshot.sh post-apply
```

If anything errors, paste it to me verbatim. The errors are the most valuable
content in the whole lab — they go straight into the log.

---

## Step 2 — Verify each control in the portal

Terraform saying "created" is not proof the control is on. Check each one.

| 📸 | Where | What it must show |
|---|---|---|
| `05-resource-group` | Resource groups → `rg-costvis` | All resources created, with tags visible |
| `06-budget-thresholds` | Cost Management → Budgets → `budget-costvis` | All four alert conditions, **including Forecasted** |
| `07-anomaly-alert` | Cost Management → Cost alerts → Anomaly alerts | The anomaly rule and its recipient |
| `08-storage-encryption` | Storage account → Settings → Configuration | Secure transfer **Enabled**, minimum TLS **1.2** |
| `09-storage-dataprotection` | Storage account → Data protection | Versioning on, soft delete 7 days |
| `10-rbac-least-privilege` | Managed identity `id-costvis-reader` → Azure role assignments | **Cost Management Reader** and nothing else |

```bash
./scripts/snapshot.sh controls-verified
```

---

## Step 3 — Prove the least-privilege control actually works

This is the step that separates a lab from a tutorial. Configuring a control is
not evidence. Testing that it denies what it should is.

Sign in as the managed identity and attempt something outside its role — read a
storage key, or create a resource. It must fail.

| 📸 | Where | What it must show |
|---|---|---|
| `11-rbac-denied` | Terminal | The `AuthorizationFailed` error when the identity attempts a write |
| `12-rbac-allowed` | Terminal | The same identity successfully reading cost data |

Two shots, side by side: denied for what it shouldn't do, allowed for what it
should. I will write the commands when you reach this step.

---

## Step 4 — Prove the alert path delivers

Budgets evaluate roughly every 12–24 hours, so waiting for a natural trigger is
impractical. Test the delivery path directly instead.

Action group → **Test action group** → Budget alert → Test.

| 📸 | Where | What it must show |
|---|---|---|
| `13-actiongroup-test` | Portal → Action group → Test | Test result succeeded |
| `14-alert-email` | Your inbox | The actual email that arrived |

The inbox screenshot matters. It closes the loop from Terraform config to an
email a human receives. Blur nothing except your own address if you prefer.

---

## Step 5 — Build the workbook cost tiles

Terraform created the workbook shell. The Cost Management tiles get added in
the portal UI, then exported back to code.

Workbook → Edit → Add query → Data source: **Azure Resource Manager**.

| 📸 | Where | What it must show |
|---|---|---|
| `15-workbook-arm-query` | Workbook edit mode | The ARM data source config: POST, the Cost Management path, the body |
| `16-workbook-rendered` | Workbook, view mode | The cost chart actually rendering data |
| `17-workbook-advanced-editor` | Workbook → Advanced Editor | The JSON you are about to copy into Terraform |

Then paste the JSON to me and I fold it into `workbook.tf`, so the finished
dashboard is reproducible from code rather than hand-built.

---

## Step 6 — Next day: confirm the export landed

Cost data has 8–24 hour latency. This step happens the day after Step 1.

| 📸 | Where | What it must show |
|---|---|---|
| `18-export-blob` | Storage account → Containers → `cost-exports` → `daily` | The CSV that Cost Management wrote |
| `19-export-contents` | The CSV opened | Real usage rows with meter names and costs |
| `20-cost-analysis-populated` | Cost Management → Cost analysis | The chart with actual data, compared against Step 0 |

```bash
./scripts/snapshot.sh export-landed
```

---

## Step 7 — Tear down and prove it

The teardown is part of the story. It shows cost discipline, and it is the step
most portfolios skip.

| 📸 | Where | What it must show |
|---|---|---|
| `21-terraform-destroy` | Terminal | `Destroy complete! Resources: 14 destroyed` |
| `22-empty-after` | Portal → Resource groups | Back to only `NetworkWatcherRG` |
| `23-final-cost` | Cost Management → Cost analysis | Total spend for the whole lab |

```bash
./scripts/snapshot.sh post-destroy
```

`23-final-cost` is the single most quotable artifact in the project. "I built,
deployed, tested, and documented a cost governance system for $X" is a sentence
that lands in an interview.

---

## What I do at each step

1. Write the brief and explain the reasoning before you run anything
2. Verify independently through `az` — I check the API, not your description
3. Capture machine-readable evidence into `docs/evidence/state/`
4. Read your screenshots and confirm they show what the case study needs
5. Log every error and fix into `LAB-LOG.md` as it happens
6. Write the case study, and a talk track of likely interview questions with
   answers grounded in what you actually did

## What you do

Run everything, make the decisions, hit the problems, and tell me what happened
in your own words. Those words become the write-up — which is also how it ends
up sounding like you wrote it, because you did.
