# =============================================================================
# TASK 1 — Foundation, identity, and storage
#
# Docs: https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs
# Search the resource name in that registry. Reading provider docs is the
# actual skill here, so the arguments are deliberately not listed for you.
#
# Available to you already (see providers.tf):
#   data.azurerm_subscription.current.id           full subscription resource ID
#   data.azurerm_subscription.current.display_name
#   var.name_prefix, var.location, var.tags, var.log_retention_days
# =============================================================================


# --- WORKED EXAMPLE ----------------------------------------------------------
# This one is done, as a pattern to follow. Storage account names are globally
# unique, lowercase alphanumeric, max 24 characters — so a random suffix stops
# `apply` colliding with an account someone else already made.

resource "random_string" "suffix" {
  length  = 6
  lower   = true
  upper   = false
  numeric = true
  special = false
}


# --- 1.1 Resource group ------------------------------------------------------
# Requirements:
#   - Name: "rg-" plus var.name_prefix
#   - Region: var.location
#   - Tagged with var.tags   (every resource in this project gets these tags —
#     that is what makes per-project cost attribution possible later)
#
# resource "azurerm_resource_group" "main" { ... }

# TODO 1.1


# --- 1.2 Log Analytics workspace ---------------------------------------------
# Requirements:
#   - Name: "law-" plus var.name_prefix
#   - Placed in the resource group from 1.1
#   - SKU: PerGB2018  (pay-as-you-go; first 5 GB/month ingested is free)
#   - Retention: var.log_retention_days
#   - Tagged
#
# Think about: why does retention default to 30 days in variables.tf rather
# than the maximum? Answer goes in DECISIONS.md.
#
# resource "azurerm_log_analytics_workspace" "main" { ... }

# TODO 1.2


# --- 1.3 User-assigned managed identity --------------------------------------
# Requirements:
#   - Name: "id-" plus var.name_prefix plus "-reader"
#   - Same resource group and region
#   - Tagged
#
# Why a separate identity at all, rather than using your own account? Because
# the thing that reads cost data should not be the thing that can also delete
# resources. Write that reasoning down.
#
# resource "azurerm_user_assigned_identity" "cost_reader" { ... }

# TODO 1.3


# --- 1.4 Role assignment -----------------------------------------------------
# Requirements:
#   - Scope: the whole subscription (cost data lives at subscription scope,
#     not resource group scope — a resource-group-scoped role cannot read a bill)
#   - Role: "Cost Management Reader"
#   - Principal: the principal_id of the identity from 1.3
#
# Trap: a user-assigned identity exposes BOTH `principal_id` and `client_id`.
# Only one of them is correct here. Picking the wrong one produces an apply
# error that looks nothing like the real cause — worth knowing which and why.
#
# resource "azurerm_role_assignment" "cost_reader" { ... }

# TODO 1.4


# --- 1.5 Storage account -----------------------------------------------------
# This holds exported billing data, so the security baseline is the point of
# the resource, not decoration.
#
# Requirements:
#   - Name: "st" + var.name_prefix + random_string.suffix.result
#     (no hyphens allowed in storage account names)
#   - Standard tier, LRS replication, StorageV2
#   - Security baseline, all of which you must set explicitly:
#       * HTTPS-only traffic
#       * minimum TLS 1.2
#       * blob containers and blobs may NOT be publicly accessible
#   - Data protection, inside a blob_properties block:
#       * blob versioning enabled
#       * soft delete for blobs, 7 days
#       * soft delete for containers, 7 days
#   - Tagged
#
# Note: the HTTPS argument was renamed in azurerm v4. If you write the v3 name
# you will get a clear error — read it rather than guessing.
#
# resource "azurerm_storage_account" "exports" { ... }

# TODO 1.5


# --- 1.6 Storage container ---------------------------------------------------
# Requirements:
#   - Name: "cost-exports"
#   - Belongs to the storage account from 1.5
#   - Access type: private
#
# In azurerm v4 this resource takes the storage account by ID, not by name.
#
# resource "azurerm_storage_container" "exports" { ... }

# TODO 1.6


# --- 1.7 Diagnostic settings -------------------------------------------------
# Requirements:
#   - Target: the BLOB SERVICE of the storage account, not the account itself.
#     The ID is the account ID with "/blobServices/default" appended.
#   - Send to the Log Analytics workspace from 1.2
#   - Capture these log categories: StorageRead, StorageWrite, StorageDelete
#   - Capture the Transaction metric category
#
# Why: cost figures are sensitive. This records WHO READ the data, not just
# what it said. Use `enabled_metric`, not `metric` — the latter is deprecated
# and disappears in provider v5.
#
# resource "azurerm_monitor_diagnostic_setting" "storage_blob" { ... }

# TODO 1.7
