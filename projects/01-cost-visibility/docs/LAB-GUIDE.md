# Lab 01 — Cost Visibility Dashboard

A walkthrough. Read the explanation, write the code, take the screenshot, move on.

---

## The problem this solves

A small business moves to the cloud. Someone estimated $5,000 a month. The first
bill is $8,000. Nobody notices until finance asks. Three months later it's
$30,000 and the money is already spent.

Nothing failed. No one was hacked. The bill just grew where nobody was looking.

**This lab builds the thing that would have caught it.** Not a report someone
has to remember to open — an automatic system that emails you when spending
starts heading somewhere bad, while there is still time to stop it.

---

## What you're building, in plain English

Think of it as a smoke detector for your cloud bill.

| Part | Plain English | Real-life equivalent |
|---|---|---|
| **Budget** | "Tell me when I've spent half, most, or all of my money" | The low-balance alert from your bank |
| **Forecast alert** | "Tell me when I'm *on pace* to overspend" | Your car saying 40 miles of fuel left, not waiting for empty |
| **Anomaly alert** | "Tell me when today looks weird vs. normal" | A fraud text when your card is used somewhere unusual |
| **Action group** | The thing that actually sends the email | The contact list the alarm company calls |
| **Cost export** | A daily copy of the bill saved to a file | Downloading your bank statement every month |
| **Storage account** | A locked folder in the cloud to keep those files | A filing cabinet with a lock |
| **Managed identity** | A robot account that can read the bill and nothing else | A key that opens the mailbox but not the house |
| **Log Analytics** | A place logs get sent so you can search them | The security camera recording |
| **Workbook** | The dashboard that shows all of it | The chart on the wall |

**The key insight:** most people set up a budget alert at 100% and stop. That
tells you the money is *already gone*. The forecast alert is the one that
matters, because it fires while you can still do something.

---

## Before you start

```bash
cd ~/Portfolio/projects/01-cost-visibility
./scripts/check.sh        # shows what's left, never touches Azure
```

Open `terraform/main.tf` in your editor. Work top to bottom.

**Terraform in one sentence:** you describe what you want in a file, and
Terraform makes Azure match it. Same idea as a shopping list — you write it
down, then something goes and gets it.

**Look up every resource here:**
<https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs>
Search the resource name, then click "Example Usage".

---

# PHASE 1 — Foundation

## Task 1.1 — Resource group

**What it is:** a folder. Everything you create in this lab goes inside it. When
you're done, deleting the folder deletes everything in it.

**Real life:** this is why cloud bills spiral. People create things in random
places, forget them, and pay for them for years. One folder per project means
one command cleans it all up.

**Write a `azurerm_resource_group` named `main` with:**

- `name` — `"rg-${var.name_prefix}"` (gives you `rg-costvis`)
- `location` — `var.location`
- `tags` — `var.tags`

**Why the variables?** Hardcoding `"rg-costvis"` means changing it in nine
places later. Variables mean changing it once.

**Why tags matter:** tags are how you answer "what did *this project* cost?"
Untagged resources are why companies can't attribute their own spending.

---

## Task 1.2 — Log Analytics workspace

**What it is:** where logs go so you can search them later. Without it, logs are
written and thrown away.

**Real life:** this is what you'd search after an incident to answer "who
accessed that, and when?" In this lab it records who read the cost data.

**Write a `azurerm_log_analytics_workspace` named `main` with:**

- `name` — `"law-${var.name_prefix}"`
- `location` — reference the resource group you just made: `azurerm_resource_group.main.location`
- `resource_group_name` — `azurerm_resource_group.main.name`
- `sku` — `"PerGB2018"`
- `retention_in_days` — `var.log_retention_days`
- `tags` — `var.tags`

**Referencing instead of repeating:** writing `azurerm_resource_group.main.name`
instead of `"rg-costvis"` tells Terraform this depends on that, so it builds
them in the right order automatically.

**Think about:** retention defaults to 30 days, not the 730-day maximum. Why
keep *less*? (Storage costs money, and old logs you'll never read are pure cost.
Real answer: retention should match how far back you'd actually investigate.)
Put your answer in `DECISIONS.md`.

### ✅ Checkpoint

```bash
./scripts/check.sh
```

Expect **10 remaining** and `Success! The configuration is valid.`

**Send me this output before continuing.**

---

# PHASE 2 — Identity and access

## Task 1.3 — Managed identity

**What it is:** a login for software instead of a person. No password exists,
so no password can leak.

**Real life:** the classic breach is a developer hardcoding a password into
code, pushing it to GitHub, and a bot finding it in minutes. A managed identity
removes the password entirely — Azure handles it invisibly.

**Write a `azurerm_user_assigned_identity` named `cost_reader` with:**
`name` (`"id-${var.name_prefix}-reader"`), `location`, `resource_group_name`, `tags`

---

## Task 1.4 — Role assignment (least privilege)

**What it is:** the identity above can currently do *nothing*. This grants it
exactly one permission: read cost data.

**Real life:** ransomware spreads because service accounts have far more access
than they need. One over-permissioned backup account can end a company. "Least
privilege" means: if this gets stolen, what's the worst that happens? Here, the
answer is "someone learns what your bill was."

**Write a `azurerm_role_assignment` named `cost_reader` with:**

- `scope` — `data.azurerm_subscription.current.id` (the whole subscription —
  billing lives at subscription level, not inside your folder)
- `role_definition_name` — `"Cost Management Reader"`
- `principal_id` — the identity's **`principal_id`**, not its `client_id`

**The trap:** a managed identity has two IDs. `principal_id` is *who it is*
(used for permissions). `client_id` is *how apps address it*. Using the wrong
one gives an error that doesn't explain itself.

---

# PHASE 3 — Storage

## Task 1.5 — Storage account (the security one)

**What it is:** cloud file storage. Your daily bill copies land here.

**Real life:** "misconfigured storage bucket" is one of the most common breach
headlines there is. Millions of records exposed, every time, because someone
left a storage container public. This task is about not being that.

**Write a `azurerm_storage_account` named `exports` with:**

Basics:
- `name` — `"st${var.name_prefix}${random_string.suffix.result}"` (no hyphens
  allowed; must be globally unique across all of Azure, hence the random suffix)
- `location`, `resource_group_name`
- `account_tier` `"Standard"`, `account_replication_type` `"LRS"`, `account_kind` `"StorageV2"`

Security — set all three explicitly:
- `https_traffic_only_enabled` = `true` → no unencrypted connections
- `min_tls_version` = `"TLS1_2"` → blocks old, breakable encryption
- `allow_nested_items_to_be_public` = `false` → **this is the one from the headlines**

Data protection — inside a `blob_properties { }` block:
- `versioning_enabled` = `true` → keeps old versions when a file is overwritten
- `delete_retention_policy { days = 7 }` → deleted files recoverable for 7 days
- `container_delete_retention_policy { days = 7 }` → same for whole containers

Plus `tags`.

**Why versioning and soft delete:** this is ransomware defense. Ransomware
encrypts your files by overwriting them. With versioning on, the originals are
still there.

---

## Task 1.6 — Storage container

**What it is:** a folder inside the storage account.

**Write a `azurerm_storage_container` named `exports` with:**
- `name` — `"cost-exports"`
- `storage_account_id` — `azurerm_storage_account.exports.id`
- `container_access_type` — `"private"`

**`"private"` means** nobody on the internet can read it without credentials.
The default in older systems was public, which is exactly how those breaches
happened.

---

## Task 1.7 — Diagnostic settings

**What it is:** turns on logging for the storage account and sends it to the
workspace from 1.2.

**Real life:** after any breach the first question is "what did they access?"
Without this, there's no answer. Cost data is sensitive — it reveals what
systems you run and how big you are.

**Write a `azurerm_monitor_diagnostic_setting` named `storage_blob` with:**
- `name` — `"diag-blob"`
- `target_resource_id` — `"${azurerm_storage_account.exports.id}/blobServices/default"`
  (the blob *service*, not the account)
- `log_analytics_workspace_id` — `azurerm_log_analytics_workspace.main.id`
- Three `enabled_log { category = ... }` blocks: `StorageRead`, `StorageWrite`, `StorageDelete`
- One `enabled_metric { category = "Transaction" }` block

**Use `enabled_metric`, not `metric`** — the old name is deprecated and will
break in the next major provider version.

### ✅ Checkpoint

```bash
./scripts/check.sh
```
Expect **5 remaining**, validation passing.

---

# PHASE 4 — Alerts

Open `terraform/monitoring.tf`.

## Task 2.1 — Action group

**What it is:** the delivery list. Alerts don't send themselves; they hand off
to an action group, which emails/texts/calls.

**Real life:** when you need to add your manager to every alert, you change one
action group instead of editing every alert rule and forgetting two.

**Write a `azurerm_monitor_action_group` named `cost` with:**
- `name` (`"ag-${var.name_prefix}"`), `resource_group_name`
- `short_name` — `"costalert"` (max 12 characters — Azure uses it as an SMS prefix)
- One email receiver per address in `var.alert_emails`, each with
  `use_common_alert_schema = true`
- `tags`

**The challenge:** `var.alert_emails` is a *list*. Writing one hardcoded
`email_receiver` block only handles one address. Look up Terraform
**`dynamic` blocks** — they generate one block per list item.

---

## Task 2.2 — Cost anomaly alert

**What it is:** Azure learns your normal daily spend and tells you when today
doesn't match.

**Real life:** a monthly budget is slow. If something starts costing $200/day on
the 3rd, the budget stays silent until the running total crosses a threshold —
maybe two weeks later, $2,800 in. The anomaly alert catches the *shape* changing
the next day.

**Write a `azurerm_cost_anomaly_alert` named `main` with:**
`name`, `display_name`, `subscription_id`, `email_subject`, `email_addresses`, `message`

---

# PHASE 5 — The budget

Open `terraform/budget.tf`. This is the centerpiece.

## Task 3.1 — Subscription budget

**Write a `azurerm_consumption_budget_subscription` named `main` with:**
- `name`, `subscription_id` (`data.azurerm_subscription.current.id` — full ID, not a bare GUID)
- `amount` — `var.monthly_budget`
- `time_grain` — `"Monthly"`
- `time_period { start_date = ...  end_date = ... }` from the variables
- **Four `notification { }` blocks**

Each notification needs `enabled`, `threshold`, `operator` (`"GreaterThanOrEqualTo"`),
`threshold_type`, `contact_emails` (`var.alert_emails`), and `contact_groups`
(`[azurerm_monitor_action_group.cost.id]`).

The four:

| threshold | threshold_type | Means |
|---|---|---|
| 50 | `"Actual"` | Half the budget is gone |
| 80 | `"Actual"` | Getting close — go look |
| 100 | `"Actual"` | Budget is gone |
| 100 | `"Forecasted"` | **On pace to blow it** |

**This is the whole lab in one table.** The first three are history. The fourth
is a warning. When an interviewer asks what you'd do differently from a default
setup, this is the answer.

---

# PHASE 6 — Export and outputs

## Task 4.1 — Cost export (`terraform/export.tf`)

**What it is:** Azure writes a CSV of your real usage to storage every day.

**Real life:** the portal is fine for "what am I spending now." It's useless for
"what did this look like in March" after the view resets. The export is your
own permanent copy.

**Write a `azurerm_subscription_cost_management_export` named `daily` with:**
`name`, `subscription_id`, `recurrence_type = "Daily"`, the two recurrence period
dates, an `export_data_storage_location { container_id, root_folder_path = "daily" }`,
and `export_data_options { type = "ActualCost", time_frame = "MonthToDate" }`.

Plus `depends_on = [azurerm_role_assignment.cost_reader]`.

**Why `depends_on` here:** Terraform normally figures out order by watching
which resources reference each other. This export never mentions the role
assignment, so Terraform doesn't know it has to wait for permissions to exist —
and would happily create an export that silently fails on its first run. You
have to say it out loud.

## Task 5.1 — Outputs (`terraform/outputs.tf`)

Print the things you'd otherwise hunt for in the portal: resource group name,
storage account name, budget name, identity client ID. Each needs a
`description`.

### ✅ Final checkpoint

```bash
./scripts/check.sh
```
Zero TODOs, validation passing, every requirement `[ok]`.

---

# PHASE 7 — Deploy

```bash
cd terraform
terraform plan -out=tfplan
```

**What `plan` does:** shows exactly what will happen without doing it. Read it.
This is the habit that prevents outages — in a real job you plan, someone
reviews it, then you apply.

> ### 📸 SCREENSHOT — `terraform-plan`
> Terminal showing `Plan: 14 to add, 0 to change, 0 to destroy.`
> ```bash
> cd .. && ./scripts/capture.sh terraform-plan "Plan output: 14 resources to add, none changed or destroyed"
> ```

```bash
terraform apply tfplan
```

> ### 📸 SCREENSHOT — `terraform-apply`
> Terminal showing `Apply complete! Resources: 14 added, 0 changed, 0 destroyed.`
> plus the outputs block.
> ```bash
> cd .. && ./scripts/capture.sh terraform-apply "Apply complete: 14 resources created, with outputs"
> ./scripts/snapshot.sh post-apply
> ```

**If it errors, paste it to me exactly.** Errors are the most valuable content
in this lab — they're what makes the write-up real instead of a tutorial.

---

# PHASE 8 — Verify every control

Terraform saying "created" is not proof a control is *on*. Check each one in the
portal. This is the difference between "I configured it" and "I verified it."

> ### 📸 SCREENSHOT — `resource-group`
> Portal → Resource groups → `rg-costvis`. Show all resources and the tags.
> ```bash
> ./scripts/capture.sh resource-group "All 14 resources deployed into rg-costvis with project tags"
> ```

> ### 📸 SCREENSHOT — `budget-thresholds`
> Cost Management → Budgets → `budget-costvis` → edit view.
> **Must show all four alert conditions including the Forecasted one.**
> ```bash
> ./scripts/capture.sh budget-thresholds "Budget with three actual thresholds and a forecasted alert"
> ```

> ### 📸 SCREENSHOT — `storage-security`
> Storage account → Settings → Configuration.
> Must show **Secure transfer: Enabled** and **Minimum TLS: 1.2**.
> ```bash
> ./scripts/capture.sh storage-security "Storage enforcing HTTPS-only and TLS 1.2 minimum"
> ```

> ### 📸 SCREENSHOT — `storage-dataprotection`
> Storage account → Data protection. Versioning on, soft delete 7 days.
> ```bash
> ./scripts/capture.sh storage-dataprotection "Blob versioning and 7-day soft delete enabled"
> ```

> ### 📸 SCREENSHOT — `least-privilege`
> Managed identity `id-costvis-reader` → Azure role assignments.
> **Must show exactly one role: Cost Management Reader.**
> ```bash
> ./scripts/capture.sh least-privilege "Identity holds exactly one role: Cost Management Reader"
> ./scripts/snapshot.sh controls-verified
> ```

---

# PHASE 9 — Prove the control actually works

**This is the most important step in the lab, and the one nobody does.**

Anyone can screenshot a settings page. That proves you clicked a toggle. Proving
the control *denies* something proves you understand it.

You'll sign in as the managed identity and try to do something outside its role.
It must fail. Then read cost data, which must succeed.

> ### 📸 SCREENSHOT — `rbac-denied`
> Terminal showing `AuthorizationFailed` when the identity tries to create or
> delete something.

> ### 📸 SCREENSHOT — `rbac-allowed`
> Terminal showing the same identity successfully reading cost data.

**Tell me when you reach this step and I'll give you the exact commands.**

**Real life:** this is what a security audit asks for. Not "is MFA enabled" but
"show me a login being blocked." Evidence beats configuration.

---

# PHASE 10 — Prove the alert reaches a human

Budgets evaluate every 12–24 hours, so waiting for a real trigger isn't
practical. Test the delivery path directly.

Portal → Action group `ag-costvis` → **Test action group** → Budget alert → Test.

> ### 📸 SCREENSHOT — `actiongroup-test`
> The test result showing success.
> ```bash
> ./scripts/capture.sh actiongroup-test "Action group test succeeded"
> ```

> ### 📸 SCREENSHOT — `alert-email`
> **Your actual inbox, with the alert email in it.**
> ```bash
> ./scripts/capture.sh alert-email "Budget alert email received — full path from Terraform to inbox"
> ```

The inbox shot closes the loop. Code → cloud → a human being told. That's the
whole point of the system.

---

# PHASE 11 — The dashboard

Terraform built the workbook shell. You'll add the cost charts in the portal,
because the portal has a proper editor for this and hand-writing the query JSON
produces dashboards that silently show nothing.

Workbook → Edit → Add → Add query → Data source: **Azure Resource Manager**.

> ### 📸 SCREENSHOT — `workbook-query` — the ARM query configuration
> ### 📸 SCREENSHOT — `workbook-rendered` — the chart actually showing data
> ### 📸 SCREENSHOT — `workbook-editor` — Advanced Editor showing the JSON

Then paste the JSON to me and I'll fold it into `workbook.tf`, so the finished
dashboard is reproducible from code instead of hand-built.

---

# PHASE 12 — Next day: real data

Cost data lags 8–24 hours. Come back tomorrow.

> ### 📸 SCREENSHOT — `export-blob`
> Storage → Containers → `cost-exports` → `daily` → the CSV Azure wrote.
> ### 📸 SCREENSHOT — `cost-analysis-populated`
> Cost analysis now showing **BUDGET: $25** and a forecast — the direct
> counterpart to your `02-baseline-cost-analysis.png`.

---

# PHASE 13 — Tear it down

Most portfolios skip this. Doing it shows cost discipline, which is the exact
skill this project is about.

```bash
cd terraform && terraform destroy
```

> ### 📸 SCREENSHOT — `terraform-destroy` — `Destroy complete! Resources: 14 destroyed.`
> ### 📸 SCREENSHOT — `final-cost` — total spend for the entire lab
> ```bash
> cd .. && ./scripts/snapshot.sh post-destroy
> ```

**`final-cost` is the most quotable artifact here.** "I built, deployed, tested,
and documented a cost governance system for $0.43" is a sentence that lands.

---

## What you'll be able to say afterward

- Built cloud cost governance as infrastructure-as-code, reproducible and destroyable
- Configured forecast-based alerting that warns before overspend, not after
- Applied a storage security baseline: TLS 1.2, no public access, versioning, soft delete
- Implemented least privilege and **proved it by testing denial**
- Verified the alert path end to end, from code to inbox
- Logged access to sensitive billing data
- Documented the gaps I couldn't close on a free tier, and why

Each of those maps to a real control an employer cares about, and you'll have a
screenshot for every one.
