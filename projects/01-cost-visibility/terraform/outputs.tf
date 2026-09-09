output "resource_group" {
  description = "Resource group holding everything in this project."
  value       = azurerm_resource_group.main.name
}

output "storage_account" {
  description = "Storage account receiving the daily cost export."
  value       = azurerm_storage_account.exports.name
}

output "workbook_url" {
  description = "Direct link to the cost dashboard in the Azure portal."
  value       = "https://portal.azure.com/#@/resource${azurerm_application_insights_workbook.cost.id}/workbook"
}

output "budget_name" {
  description = "Name of the subscription budget."
  value       = azurerm_consumption_budget_subscription.main.name
}

output "cost_reader_client_id" {
  description = "Client ID of the least-privilege identity used to read cost data."
  value       = azurerm_user_assigned_identity.cost_reader.client_id
}

output "monthly_budget_usd" {
  description = "Budget the alert thresholds are calculated against."
  value       = var.monthly_budget
}
