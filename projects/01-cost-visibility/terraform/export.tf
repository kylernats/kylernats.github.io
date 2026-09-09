# =============================================================================
# TASK 4 — Daily cost export
# =============================================================================

# --- 4.1 Cost management export ----------------------------------------------
# Cost Analysis in the portal is fine for reading a number today. It is useless
# for "what did this look like six months ago" once retention rolls over. The
# export writes a CSV of real usage into blob storage every day, which becomes
# the raw history everything else can be rebuilt from.
#
# Requirements:
#   - Name: "export-" plus var.name_prefix plus "-daily"
#   - Scoped to the current subscription
#   - Runs Daily, between var.budget_start_date and var.budget_end_date
#   - Writes into the container from 1.6, under a root folder path "daily"
#   - Export data options:
#       type       = ActualCost      (what was billed; the alternative,
#                                     AmortizedCost, spreads reservation
#                                     purchases across the period they cover)
#       time_frame = MonthToDate     (each run rewrites the month so far, so
#                                     the newest file is always complete)
#
#   - depends_on the role assignment from 1.4. Without it Terraform may create
#     the export before permissions exist and the first run fails silently.
#     Think about why an explicit depends_on is needed when Terraform normally
#     works dependencies out on its own.
#
# resource "azurerm_subscription_cost_management_export" "daily" { ... }

# TODO 4.1
