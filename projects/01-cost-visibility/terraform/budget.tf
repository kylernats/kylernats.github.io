# =============================================================================
# TASK 3 — The budget
#
# This is the centrepiece of the project. Get the threshold design right and
# the rest of the lab is plumbing.
# =============================================================================

# --- 3.1 Subscription budget -------------------------------------------------
# Requirements:
#   - Name: "budget-" plus var.name_prefix
#   - Scoped to the current subscription
#   - Amount: var.monthly_budget, resetting Monthly
#   - Time period: var.budget_start_date to var.budget_end_date
#
#   - FOUR notification blocks:
#       50%   of actual spend
#       80%   of actual spend
#       100%  of actual spend
#       100%  of FORECASTED spend
#
#     Each one: enabled, operator GreaterThanOrEqualTo, sending to both
#     var.alert_emails and the action group from 2.1.
#
# The actual/forecasted split is the entire idea. Actual thresholds are
# backward-looking — they tell you money is already gone. The forecast alert
# fires when the month is PROJECTED to exceed budget, which is the only one
# that arrives while there is still time to act. That is the alert that would
# have caught a $5K estimate turning into $30K.
#
# Two gotchas:
#   - the subscription argument wants the full resource ID, not a bare GUID
#   - thresholds are numbers, and the attribute controlling actual vs
#     forecasted is a separate argument from the threshold itself
#
# resource "azurerm_consumption_budget_subscription" "main" { ... }

# TODO 3.1
