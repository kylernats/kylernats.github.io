# ---------------------------------------------------------------------------
# Budget
#
# Four notifications, and the split between Actual and Forecasted is the
# whole point. Actual tells you what already happened. Forecasted tells you
# where the month is heading, which is the only one that arrives early enough
# to do anything about.
# ---------------------------------------------------------------------------
resource "azurerm_consumption_budget_subscription" "main" {
  name            = "budget-${var.name_prefix}"
  subscription_id = data.azurerm_subscription.current.id

  amount     = var.monthly_budget
  time_grain = "Monthly"

  time_period {
    start_date = var.budget_start_date
    end_date   = var.budget_end_date
  }

  # Half the budget spent. Informational.
  notification {
    enabled        = true
    threshold      = 50.0
    operator       = "GreaterThanOrEqualTo"
    threshold_type = "Actual"
    contact_emails = var.alert_emails
    contact_groups = [azurerm_monitor_action_group.cost.id]
  }

  # Getting close. Time to look at what is running.
  notification {
    enabled        = true
    threshold      = 80.0
    operator       = "GreaterThanOrEqualTo"
    threshold_type = "Actual"
    contact_emails = var.alert_emails
    contact_groups = [azurerm_monitor_action_group.cost.id]
  }

  # Budget is gone.
  notification {
    enabled        = true
    threshold      = 100.0
    operator       = "GreaterThanOrEqualTo"
    threshold_type = "Actual"
    contact_emails = var.alert_emails
    contact_groups = [azurerm_monitor_action_group.cost.id]
  }

  # Projected to blow the budget before month end. This is the early warning,
  # and it is the one that would have caught the $5K estimate turning into
  # $30K while there was still time to stop it.
  notification {
    enabled        = true
    threshold      = 100.0
    operator       = "GreaterThanOrEqualTo"
    threshold_type = "Forecasted"
    contact_emails = var.alert_emails
    contact_groups = [azurerm_monitor_action_group.cost.id]
  }
}
