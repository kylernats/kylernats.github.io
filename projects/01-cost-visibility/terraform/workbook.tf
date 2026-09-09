# Workbook resource names must be GUIDs. This one is generated once and kept
# in state, so the workbook keeps its identity across applies.
resource "random_uuid" "workbook" {}

# ---------------------------------------------------------------------------
# Cost dashboard
#
# This is the starter workbook. It is deliberately built in two stages:
#
#   1. Terraform creates it with the structure below, which is enough to prove
#      the resource deploys and the Log Analytics tile returns data.
#   2. The Cost Management tiles get added through the portal UI, which has a
#      proper editor for the Azure Resource Manager data source. Then the JSON
#      is exported from Advanced Editor and pasted back here.
#
# Stage 2 is done in the portal on purpose. Hand-writing ARM data source JSON
# is how you end up with a dashboard that silently returns nothing.
# ---------------------------------------------------------------------------
resource "azurerm_application_insights_workbook" "cost" {
  name                = random_uuid.workbook.result
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  display_name        = "Cost Visibility"
  source_id           = lower(azurerm_log_analytics_workspace.main.id)

  data_json = jsonencode({
    "$schema" = "https://github.com/Microsoft/Application-Insights-Workbooks/blob/master/schema/workbook.json"
    version   = "Notebook/1.0"

    items = [
      {
        type = 1
        name = "header"
        content = {
          json = join("\n", [
            "# Cost Visibility",
            "",
            "Spend against a **$${var.monthly_budget}/month** budget for subscription `${data.azurerm_subscription.current.display_name}`.",
            "",
            "Alerts fire at 50%, 80%, and 100% of actual spend, plus a forecast warning when the month is projected to go over.",
          ])
        }
      },
      {
        type = 9
        name = "parameters"
        content = {
          version = "KqlParameterItem/1.0"
          parameters = [
            {
              id      = "timerange"
              version = "KqlParameterItem/1.0"
              name    = "TimeRange"
              label   = "Time range"
              type    = 4
              value   = { durationMs = 2592000000 }
              typeSettings = {
                selectableValues = [
                  { durationMs = 604800000 },
                  { durationMs = 2592000000 },
                  { durationMs = 7776000000 },
                ]
              }
            }
          ]
        }
      },
      {
        type = 1
        name = "links-header"
        content = {
          json = "## Native cost views"
        }
      },
      {
        type = 11
        name = "links"
        content = {
          version = "LinkItem/1.0"
          style   = "list"
          links = [
            {
              linkTarget         = "Url"
              linkLabel          = "Cost Analysis"
              subTarget          = "https://portal.azure.com/#view/Microsoft_Azure_CostManagement/Menu/~/costanalysis"
              style              = "link"
              linkIsContextBlade = false
            },
            {
              linkTarget = "Url"
              linkLabel  = "Budgets"
              subTarget  = "https://portal.azure.com/#view/Microsoft_Azure_CostManagement/Menu/~/budgets"
              style      = "link"
            },
          ]
        }
      },
      {
        type = 1
        name = "access-header"
        content = {
          json = join("\n", [
            "## Who read the cost data",
            "",
            "Cost figures are sensitive. This tile reads the storage diagnostic logs so there is a record of access to the exported data, not just the numbers themselves.",
          ])
        }
      },
      {
        type = 3
        name = "storage-access"
        content = {
          version = "KqlItem/1.0"
          query = join(" ", [
            "StorageBlobLogs",
            "| where TimeGenerated {TimeRange}",
            "| summarize Operations = count() by bin(TimeGenerated, 1d), OperationName",
            "| order by TimeGenerated asc",
          ])
          size          = 0
          queryType     = 0
          resourceType  = "microsoft.operationalinsights/workspaces"
          timeContext   = { durationMs = 2592000000 }
          visualization = "timechart"
          noDataMessage = "No storage access recorded yet. Diagnostic logs take up to 15 minutes to surface after the first read."
        }
      },
    ]
  })

  tags = var.tags
}
