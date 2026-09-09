# =============================================================================
# TASK 2 — Alert delivery and anomaly detection
# =============================================================================

# --- 2.1 Action group --------------------------------------------------------
# An action group is the delivery mechanism for an alert. Budgets can email
# addresses directly, so routing through an action group is a deliberate
# choice: swapping in SMS, a webhook, or a ticket queue later becomes a change
# in one place instead of four.
#
# Requirements:
#   - Name: "ag-" plus var.name_prefix
#   - In the resource group from 1.1
#   - short_name: "costalert"   (max 12 chars — Azure uses it as an SMS prefix)
#   - One email receiver per address in var.alert_emails
#   - Enable the common alert schema on each receiver
#   - Tagged
#
# var.alert_emails is a LIST, so hardcoding one receiver block is wrong. Look
# up `dynamic` blocks in Terraform — inside one, `each.key` gives you the list
# index and `each.value` the address, where `each` is named after the block.
#
# resource "azurerm_monitor_action_group" "cost" { ... }

# TODO 2.1


# --- 2.2 Cost anomaly alert --------------------------------------------------
# A monthly budget is blunt. If something starts costing money on the 3rd, the
# budget stays silent until the running total crosses a threshold — possibly
# two weeks later. Anomaly detection compares daily spend against the pattern
# Azure has learned and flags the shape changing.
#
# Requirements:
#   - Name: "anomaly-" plus var.name_prefix
#   - A human-readable display name
#   - Scoped to the current subscription
#   - Email subject line, and recipients from var.alert_emails
#   - A message telling the reader what to go look at
#
# Hint: search the registry for "cost anomaly".
#
# resource "azurerm_cost_anomaly_alert" "main" { ... }

# TODO 2.2
