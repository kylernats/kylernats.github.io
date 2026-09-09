# ---------------------------------------------------------------------------
# Daily cost export
#
# Cost Analysis in the portal is fine for looking at a number. It is useless
# for answering "what did this look like six months ago" once the retention
# window rolls over. The export drops a CSV of actual usage into blob storage
# every day, which is the raw history everything else can be rebuilt from.
# ---------------------------------------------------------------------------
resource "azurerm_subscription_cost_management_export" "daily" {
  name                         = "export-${var.name_prefix}-daily"
  subscription_id              = data.azurerm_subscription.current.id
  recurrence_type              = "Daily"
  recurrence_period_start_date = var.budget_start_date
  recurrence_period_end_date   = var.budget_end_date

  export_data_storage_location {
    container_id     = azurerm_storage_container.exports.id
    root_folder_path = "daily"
  }

  export_data_options {
    # ActualCost is what was billed. The alternative, AmortizedCost, spreads
    # reservation purchases across the period they cover. With no reservations
    # in play the two are identical, but ActualCost is what the invoice says.
    type = "ActualCost"

    # Each daily run rewrites the month so far, so the newest file is always
    # the complete picture of the current month.
    time_frame = "MonthToDate"
  }

  depends_on = [azurerm_role_assignment.cost_reader]
}
