# Storage account names are globally unique and allow no punctuation, so a
# short random suffix keeps `terraform apply` from colliding with someone
# else's account name.
resource "random_string" "suffix" {
  length  = 6
  lower   = true
  upper   = false
  numeric = true
  special = false
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${var.name_prefix}"
  location = var.location
  tags     = var.tags
}

resource "azurerm_log_analytics_workspace" "main" {
  name                = "law-${var.name_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  # PerGB2018 is the pay-as-you-go SKU. The first 5 GB ingested per month is
  # free, and this workspace will take in a tiny fraction of that.
  sku               = "PerGB2018"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# ---------------------------------------------------------------------------
# Identity
#
# The identity that reads cost data is separate from my user account and holds
# exactly one role. If it leaked, the worst an attacker gets is the ability to
# read a bill. It cannot create, modify, or delete anything.
# ---------------------------------------------------------------------------
resource "azurerm_user_assigned_identity" "cost_reader" {
  name                = "id-${var.name_prefix}-reader"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

resource "azurerm_role_assignment" "cost_reader" {
  scope                = data.azurerm_subscription.current.id
  role_definition_name = "Cost Management Reader"
  principal_id         = azurerm_user_assigned_identity.cost_reader.principal_id
}

# ---------------------------------------------------------------------------
# Storage for the daily cost export
# ---------------------------------------------------------------------------
resource "azurerm_storage_account" "exports" {
  name                = "st${var.name_prefix}${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  # --- Security baseline -------------------------------------------------
  https_traffic_only_enabled      = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false

  blob_properties {
    # Versioning plus soft delete means a bad overwrite or an accidental
    # delete is recoverable. This is the same control that project 02 is
    # built around, applied here on a smaller scale.
    versioning_enabled = true

    delete_retention_policy {
      days = 7
    }

    container_delete_retention_policy {
      days = 7
    }
  }

  tags = var.tags
}

resource "azurerm_storage_container" "exports" {
  name                  = "cost-exports"
  storage_account_id    = azurerm_storage_account.exports.id
  container_access_type = "private"
}

# Send storage access logs to Log Analytics so there is a record of who read
# the cost data, not just what it said.
resource "azurerm_monitor_diagnostic_setting" "storage_blob" {
  name                       = "diag-blob"
  target_resource_id         = "${azurerm_storage_account.exports.id}/blobServices/default"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category = "StorageRead"
  }

  enabled_log {
    category = "StorageWrite"
  }

  enabled_log {
    category = "StorageDelete"
  }

  enabled_metric {
    category = "Transaction"
  }
}
