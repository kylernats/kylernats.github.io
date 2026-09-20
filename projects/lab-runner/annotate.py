#!/usr/bin/env python3
"""Attach a plain-English note to every line of the reference code.

Notes are keyed by a distinctive substring of the line rather than by line
number, so they survive reformatting of the reference solution.

    python3 projects/lab-runner/annotate.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LAB = ROOT / "labs" / "01-cost-visibility.json"

# task id -> list of (substring to match, plain-English note)
NOTES = {
"1.1": [
 ('resource "azurerm_resource_group"', 'Start of the block. `azurerm_resource_group` is the kind of thing being made. `"main"` is my own nickname for it, used when other code needs to point at this one. Azure never sees the nickname.'),
 ('name     =', 'The name Azure actually shows. `${...}` drops a variable into the string. `var.name_prefix` is `costvis`, so this comes out as `rg-costvis`.'),
 ('location =', 'Which Azure region it lives in. Comes from a variable so I change it in one place instead of nine.'),
 ('tags     =', 'Labels stuck on the resource. These are what let me answer "what did this project cost" later. Untagged resources are invisible in a cost breakdown.'),
],
"1.2": [
 ('resource "azurerm_log_analytics_workspace"', 'Creates the place logs get sent. Without something like this, logs are generated and thrown away.'),
 ('name                =', 'Becomes `law-costvis`. Same variable trick as before.'),
 ('location            =', 'Reuses the resource group\'s region instead of me typing the region again. Pointing at another resource also tells Terraform to build that one first.'),
 ('resource_group_name =', 'Puts this workspace inside the folder from 1.1.'),
 ('sku               =', 'The pricing plan. `PerGB2018` means pay per gigabyte of logs taken in. The first 5 GB each month is free, and this lab uses a tiny fraction of that.'),
 ('retention_in_days =', 'How many days logs are kept before Azure deletes them. Longer retention costs more, so 30 days is a deliberate choice, not a default.'),
 ('tags = var.tags', 'Same labels as everything else in the project.'),
],
"1.3": [
 ('resource "azurerm_user_assigned_identity"', 'Creates a login for software rather than a person. Nothing about it has a password, which means there is no password to accidentally commit to GitHub.'),
 ('name                =', 'Becomes `id-costvis-reader`. The name says what it is allowed to do, which matters when you have forty of these.'),
 ('location            =', 'Region. Same one as everything else.'),
 ('resource_group_name =', 'Lives in the project folder.'),
 ('tags                =', 'Project labels.'),
],
"1.4": [
 ('resource "azurerm_role_assignment"', 'This is the line that actually grants permission. Until this exists, the identity from 1.3 can do literally nothing.'),
 ('scope                =', 'Where the permission applies. This is the whole subscription, because billing data lives at subscription level. A resource-group scope would not be able to read a bill at all.'),
 ('role_definition_name =', 'Which permission. `Cost Management Reader` is a built-in Azure role that can read cost data and nothing else. Not Contributor, not Owner, not even Reader.'),
 ('principal_id         =', 'Who gets it. `principal_id` is the identity\'s object ID, meaning *who it is*. The identity also has a `client_id`, which is how apps address it. Using `client_id` here fails with an error that does not mention `client_id` anywhere.'),
],
"1.5": [
 ('resource "azurerm_storage_account"', 'Creates cloud file storage. The daily copies of the bill land here.'),
 ('name                =', 'Storage account names have to be unique across all of Azure, and allow only lowercase letters and numbers. That is why a random 6-character suffix gets glued on the end.'),
 ('account_tier             =', 'Standard is the cheap, disk-backed option. Premium is SSD and costs far more for no benefit here.'),
 ('account_replication_type =', 'LRS keeps three copies inside one datacenter. The alternatives copy across regions and cost more to protect data that regenerates daily anyway.'),
 ('account_kind             =', 'The current generation of storage account. There is no reason to pick an older one.'),
 ('https_traffic_only_enabled      =', 'Refuses plain HTTP. Anything connecting has to use encryption in transit.'),
 ('min_tls_version                 =', 'Refuses old, breakable encryption. TLS 1.0 and 1.1 have known attacks against them.'),
 ('allow_nested_items_to_be_public =', 'This is the big one. It makes it impossible for anyone to flip a container to public. "Misconfigured storage bucket" breaches are this setting being wrong.'),
 ('blob_properties {', 'Opens a sub-block. Everything inside applies to blobs rather than to the account itself.'),
 ('versioning_enabled =', 'Keeps the old copy whenever a file is overwritten. This is ransomware defence: ransomware encrypts by overwriting, and versioning means the originals are still sitting there.'),
 ('delete_retention_policy {', 'Opens the soft-delete settings for individual files.'),
 ('days = 7', 'A deleted file is recoverable for 7 days instead of being gone instantly.'),
 ('container_delete_retention_policy {', 'The same protection, but for someone deleting a whole container rather than one file.'),
 ('tags = var.tags', 'Project labels.'),
],
"1.6": [
 ('resource "azurerm_storage_container"', 'Creates a folder inside the storage account from 1.5.'),
 ('name                  =', 'The folder name. Azure Cost Management will write into this.'),
 ('storage_account_id    =', 'Which account it belongs to. In provider version 4 this takes the account\'s ID; older examples online pass the account *name*, which no longer works.'),
 ('container_access_type =', '`private` means nobody on the internet can read it without credentials. Older systems defaulted to public, which is exactly how those breach headlines happen.'),
],
"1.7": [
 ('resource "azurerm_monitor_diagnostic_setting"', 'Turns logging on for the storage account and points it at the workspace from 1.2.'),
 ('name                       =', 'Just a label for this logging rule.'),
 ('target_resource_id         =', 'What to collect logs from. Appending `/blobServices/default` targets the blob service specifically. Pointing at the bare account ID collects account-level events and misses the file reads, which are the interesting part.'),
 ('log_analytics_workspace_id =', 'Where the logs are sent.'),
 ('category = "StorageRead"', 'Records every read. This is the one that answers "who looked at the cost data".'),
 ('category = "StorageWrite"', 'Records every write, so I can confirm the daily export actually ran.'),
 ('category = "StorageDelete"', 'Records deletions. If something vanishes, there is a record of it.'),
 ('enabled_metric {', 'Numeric counters rather than individual events. Use `enabled_metric`, not `metric` — the old name is deprecated and disappears in provider version 5.'),
],
"2.1": [
 ('resource "azurerm_monitor_action_group"', 'The delivery mechanism. Alerts do not send themselves; they hand off to an action group, which emails, texts, or calls a webhook.'),
 ('name                =', 'Becomes `ag-costvis`.'),
 ('resource_group_name =', 'Lives in the project folder.'),
 ('short_name          =', 'Maximum 12 characters. Azure uses it as the prefix on SMS messages, which is why it is capped so short.'),
 ('dynamic "email_receiver"', 'Generates one `email_receiver` block per item in a list. Writing a single hardcoded block would only ever handle one address.'),
 ('for_each =', 'The list being looped over. One receiver gets generated for each address in it.'),
 ('content {', 'What each generated block contains. This runs once per list item.'),
 ('name                    =', 'Each receiver needs a unique name, so the list index gets appended: `email-0`, `email-1`, and so on. `email_receiver.key` is that index.'),
 ('email_address           =', 'The actual address. `.value` is the current item from the list.'),
 ('use_common_alert_schema =', 'Sends alerts in Azure\'s standard payload format, so a webhook or ticket system can parse them without custom code per alert type.'),
],
"2.2": [
 ('resource "azurerm_cost_anomaly_alert"', 'Azure learns what your normal daily spend looks like and tells you when today does not match. A monthly budget cannot do this — it only sees the running total.'),
 ('name            =', 'Internal name for the rule.'),
 ('display_name    =', 'What shows in the portal. Worth making readable.'),
 ('subscription_id =', 'Which subscription to watch.'),
 ('email_subject   =', 'The subject line of the email you will get. Make it obvious at a glance.'),
 ('email_addresses =', 'Who receives it. This alert emails directly rather than going through the action group.'),
 ('message         =', 'Body text. Worth saying where to go look, because the alert itself does not tell you which resource caused it.'),
],
"3.1": [
 ('resource "azurerm_consumption_budget_subscription"', 'The centrepiece. A spending limit that emails you as you approach it.'),
 ('name            =', 'Becomes `budget-costvis`.'),
 ('subscription_id =', 'This wants the full resource ID (`/subscriptions/...`), not the bare GUID. Passing the GUID gives a confusing scope error.'),
 ('amount     =', 'The budget in dollars. Every threshold below is a percentage of this number.'),
 ('time_grain =', 'Monthly means the counter resets on the 1st.'),
 ('time_period {', 'When the budget is active. Start date has to be UTC midnight on the first of a month.'),
 ('threshold      = 50.0', 'Fires at 50% of the budget. Informational — just telling me the month is moving.'),
 ('threshold      = 80.0', 'Fires at 80%. This is the "go look at what is running" alert.'),
 ('operator       =', '`GreaterThanOrEqualTo` means fire at or above the threshold, not exactly on it.'),
 ('threshold_type = "Actual"', 'Based on money already spent. Backward-looking: by the time this fires, the money is gone.'),
 ('threshold_type = "Forecasted"', 'Based on where the month is *projected* to land. This is the one that arrives while there is still time to act, and the reason this project exists.'),
 ('contact_emails =', 'Addresses emailed directly by the budget.'),
 ('contact_groups =', 'Also route through the action group from 2.1, so adding SMS later is one change instead of four.'),
],
"4.1": [
 ('resource "azurerm_subscription_cost_management_export"', 'Tells Azure to write a CSV of real usage into storage on a schedule. Cost Analysis in the portal is fine for today; this is how you still have March\'s numbers in September.'),
 ('name                         =', 'Name of the scheduled export.'),
 ('subscription_id              =', 'Which subscription\'s costs to export.'),
 ('recurrence_type              =', 'Daily. Every day it writes a fresh file.'),
 ('recurrence_period_start_date =', 'When the schedule starts running.'),
 ('recurrence_period_end_date   =', 'When it stops. Has to be in the future or the export never runs.'),
 ('export_data_storage_location {', 'Opens the block describing where the file goes.'),
 ('container_id     =', 'The container from 1.6.'),
 ('root_folder_path =', 'A subfolder inside that container, so the files are not loose at the root.'),
 ('export_data_options {', 'Opens the block describing what goes in the file.'),
 ('type = "ActualCost"', 'What was actually billed. The alternative, `AmortizedCost`, spreads big upfront purchases across the months they cover. With no reservations in play they are identical, but ActualCost matches the invoice.'),
 ('time_frame = "MonthToDate"', 'Each run rewrites the whole month so far, so the newest file is always the complete picture rather than one day in isolation.'),
 ('depends_on =', 'Forces Terraform to create the role assignment first. Terraform normally works out order by noticing which resources reference each other, but this export never mentions the role assignment, so it has no idea it has to wait. Without this line it can create an export that silently fails its first run.'),
],
"5.1": [
 ('output "resource_group"', 'Prints a value after `terraform apply` finishes. `"resource_group"` is the label it shows up under.'),
 ('description = "Resource group', 'A note for whoever reads this later, including me in six months. Terraform does not require it.'),
 ('value       = azurerm_resource_group.main.name', 'What actually gets printed. Saves hunting through the portal for the name.'),
 ('output "storage_account"', 'The storage account name, which is partly random, so this is the only convenient way to find it.'),
 ('output "workbook_url"', 'Builds a direct portal link to the dashboard, so I do not have to navigate there by hand.'),
 ('output "budget_name"', 'Confirms the budget got created and under what name.'),
 ('output "cost_reader_client_id"', 'The identity\'s client ID, needed when testing that least privilege actually denies things in phase 9.'),
 ('output "monthly_budget_usd"', 'Echoes back the budget so the alert thresholds are not a mystery later.'),
],
}


def main() -> None:
    lab = json.loads(LAB.read_text())
    done = missed = 0

    for ph in lab["phases"]:
        for st in ph["steps"]:
            notes = NOTES.get(st.get("id"))
            if not notes:
                continue
            hints = st.get("hints") or []
            code = next((h["code"] for h in reversed(hints) if h.get("code")), None)
            if not code:
                continue

            rows, used = [], set()
            for line in code.split("\n"):
                note = ""
                for key, text in notes:
                    if key in line and key not in used:
                        note, _ = text, used.add(key)
                        break
                rows.append({"code": line, "note": note})

            unused = [k for k, _ in notes if k not in used]
            if unused:
                missed += len(unused)
                print(f"  {st['id']}: no line matched {unused}")

            st["annotated"] = rows
            done += 1

    LAB.write_text(json.dumps(lab, indent=2))
    print(f"\nannotated {done} tasks; {missed} unmatched note key(s)")


if __name__ == "__main__":
    main()
