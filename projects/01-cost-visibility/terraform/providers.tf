terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  # Provider v4 requires the subscription explicitly rather than inheriting
  # whatever `az account` happens to be pointed at. That is a good thing:
  # it means this config cannot accidentally deploy into the wrong place.
  subscription_id = var.subscription_id

  features {}
}

data "azurerm_subscription" "current" {}

data "azurerm_client_config" "current" {}
