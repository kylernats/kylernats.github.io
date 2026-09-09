# ---------------------------------------------------------------------------
# Alert delivery
#
# An action group is the delivery mechanism. Email only for now. The reason to
# route budget alerts through an action group rather than straight to an email
# list is that swapping in SMS, a webhook, or a ticket queue later is a change
# in one place instead of four.
# ---------------------------------------------------------------------------
resource "azurerm_monitor_action_group" "cost" {
  name                = "ag-${var.name_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "costalert"

  dynamic "email_receiver" {
    for_each = var.alert_emails

    content {
      name                    = "email-${email_receiver.key}"
      email_address           = email_receiver.value
      use_common_alert_schema = true
    }
  }

  tags = var.tags
}

# ---------------------------------------------------------------------------
# Anomaly detection
#
# A monthly budget is a blunt instrument. If something starts costing money on
# the 3rd, the budget stays quiet until the total crosses a threshold, which
# could be two weeks later. Anomaly detection compares daily spend against the
# pattern Azure has learned and flags the shape changing.
# ---------------------------------------------------------------------------
resource "azurerm_cost_anomaly_alert" "main" {
  name            = "anomaly-${var.name_prefix}"
  display_name    = "Daily cost anomaly"
  subscription_id = data.azurerm_subscription.current.id
  email_subject   = "Azure cost anomaly detected"
  email_addresses = var.alert_emails
  message         = "Daily spend deviated from the learned pattern. Check Cost Analysis for the responsible resource."
}
