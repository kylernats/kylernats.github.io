#!/usr/bin/env bash
# check.sh — progress and correctness check for the Terraform you are writing.
# Run this as often as you like. It never touches Azure.

set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../terraform"

echo "=============================================="
echo " Lab 01 — Terraform progress"
echo "=============================================="
echo

remaining=$(grep -h "^# TODO" ./*.tf 2>/dev/null | wc -l | tr -d ' ')

if [[ "$remaining" -gt 0 ]]; then
  echo "Remaining tasks: $remaining"
  echo
  grep -Hn "^# TODO" ./*.tf | sed 's/:# TODO/  →  /' | sed 's|^|  |'
  echo
else
  echo "  All TODO markers cleared."
  echo
fi

echo "---- terraform fmt ----"
if terraform fmt -check -recursive . >/dev/null 2>&1; then
  echo "  formatting OK"
else
  echo "  needs formatting — run: terraform fmt -recursive ."
fi
echo

echo "---- terraform validate ----"
if out=$(terraform validate -no-color 2>&1); then
  echo "$out" | sed 's|^|  |'
else
  echo "$out" | sed 's|^|  |'
  echo
  echo "  Validation failures are expected while TODOs remain."
  exit 0
fi
echo

# Once it validates, check the requirements that validation cannot catch.
if [[ "$remaining" -eq 0 ]]; then
  echo "---- requirement checks ----"
  chk() { if grep -qE "$2" ./*.tf 2>/dev/null; then echo "  [ok]   $1"; else echo "  [MISS] $1"; fi; }

  chk "min TLS 1.2 on storage"              'min_tls_version.*TLS1_2'
  chk "public blob access disabled"         'allow_nested_items_to_be_public.*false'
  chk "HTTPS-only traffic"                  'https_traffic_only_enabled.*true'
  chk "blob versioning enabled"             'versioning_enabled.*true'
  chk "blob soft delete"                    'delete_retention_policy'
  chk "least-privilege role"                'Cost Management Reader'
  chk "forecasted budget alert"             'Forecasted'
  chk "four budget notifications"           'notification'
  chk "diagnostic logs to Log Analytics"    'log_analytics_workspace_id'
  chk "enabled_metric (not deprecated)"     'enabled_metric'
  chk "export uses ActualCost"              'ActualCost'
  chk "export depends on role assignment"   'depends_on'
  chk "resources tagged"                    'tags\s*=\s*var\.tags'
  echo
  echo "  All clear? Next: terraform plan -out=tfplan"
fi
