variable "subscription_id" {
  description = "Azure subscription ID to deploy into."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.subscription_id))
    error_message = "subscription_id must be a GUID."
  }
}

variable "location" {
  description = "Azure region for the resource group and storage."
  type        = string
  default     = "eastus2"
}

variable "name_prefix" {
  description = "Prefix for resource names. Keep it short; storage accounts cap at 24 chars."
  type        = string
  default     = "costvis"

  validation {
    condition     = can(regex("^[a-z0-9]{3,12}$", var.name_prefix))
    error_message = "name_prefix must be 3-12 lowercase alphanumeric characters."
  }
}

variable "alert_emails" {
  description = "Addresses that receive budget and anomaly alerts."
  type        = list(string)

  validation {
    condition     = length(var.alert_emails) > 0
    error_message = "Provide at least one alert email address."
  }
}

variable "monthly_budget" {
  description = "Monthly budget in USD. Alerts fire at percentages of this number."
  type        = number
  default     = 25

  validation {
    condition     = var.monthly_budget > 0
    error_message = "monthly_budget must be greater than zero."
  }
}

variable "budget_start_date" {
  description = "First day of the month the budget starts, UTC midnight."
  type        = string
  default     = "2026-09-01T00:00:00Z"
}

variable "budget_end_date" {
  description = "When the budget stops evaluating."
  type        = string
  default     = "2027-09-01T00:00:00Z"
}

variable "log_retention_days" {
  description = "Log Analytics retention. 30 days stays inside the free allowance."
  type        = number
  default     = 30
}

variable "tags" {
  description = "Tags applied to every resource. Used later to attribute cost per project."
  type        = map(string)
  default = {
    project     = "01-cost-visibility"
    owner       = "kyler"
    managed_by  = "terraform"
    environment = "lab"
  }
}
