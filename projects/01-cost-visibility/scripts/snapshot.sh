#!/usr/bin/env bash
# snapshot.sh <label>
#
# Machine-readable proof of what exists in Azure right now. This is the
# evidence that does not depend on a screenshot being honest: raw API output,
# timestamped, committed to the repo.

set -euo pipefail

LABEL="${1:?usage: snapshot.sh <label>}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$PROJECT_DIR/docs/evidence/state/$(date '+%Y%m%d-%H%M')-${LABEL}"
mkdir -p "$OUT"

SUB=$(az account show --query id -o tsv)
RG="rg-costvis"

echo "Capturing Azure state -> ${OUT#"$PROJECT_DIR/"}"

az resource list --resource-group "$RG" \
  --query "[].{name:name,type:type,location:location}" -o json \
  > "$OUT/resources.json" 2>/dev/null || echo "[]" > "$OUT/resources.json"

az consumption budget list --query "[].{name:name,amount:amount,timeGrain:timeGrain,currentSpend:currentSpend}" \
  -o json > "$OUT/budgets.json" 2>/dev/null || echo "[]" > "$OUT/budgets.json"

az role assignment list --scope "/subscriptions/$SUB" \
  --query "[?roleDefinitionName=='Cost Management Reader'].{role:roleDefinitionName,principal:principalName,scope:scope}" \
  -o json > "$OUT/role-assignments.json" 2>/dev/null || echo "[]" > "$OUT/role-assignments.json"

az costmanagement export list --scope "/subscriptions/$SUB" \
  -o json > "$OUT/cost-exports.json" 2>/dev/null || echo "[]" > "$OUT/cost-exports.json"

# What the bill actually says, which is the whole point of the project.
az consumption usage list --top 50 \
  --query "[].{date:usageStart,service:meterName,cost:pretaxCost,currency:currency}" \
  -o json > "$OUT/usage.json" 2>/dev/null || echo "[]" > "$OUT/usage.json"

{
  echo "# Snapshot: $LABEL"
  echo
  echo "Captured $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "Subscription: $SUB"
  echo
  echo "| File | Records |"
  echo "|---|---|"
  for f in "$OUT"/*.json; do
    n=$(python3 -c "import json;d=json.load(open('$f'));print(len(d) if isinstance(d,list) else 1)" 2>/dev/null || echo "?")
    echo "| \`$(basename "$f")\` | $n |"
  done
} > "$OUT/README.md"

cat "$OUT/README.md"
