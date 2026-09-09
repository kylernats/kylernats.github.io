#!/usr/bin/env bash
# capture.sh <slug> [description]
#
# Grabs the newest screenshot off the Desktop, renames it with a sequence
# number and a slug, and files it under docs/evidence/screenshots/.
# Also appends a line to the evidence index so every image has a caption.
#
#   ./scripts/capture.sh budget-alerts "Budget showing four notification rules"

set -euo pipefail

SLUG="${1:?usage: capture.sh <slug> [description]}"
DESC="${2:-}"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$PROJECT_DIR/docs/evidence/screenshots"
INDEX="$PROJECT_DIR/docs/evidence/screenshots/INDEX.md"
mkdir -p "$DEST"

# macOS names these "Screenshot 2026-09-09 at 4.03.12 PM.png" (or "Screen Shot"
# on older releases). Take whichever is newest.
latest=$(ls -t "$HOME/Desktop/"Screen*.png 2>/dev/null | head -1 || true)

if [[ -z "$latest" ]]; then
  echo "No screenshot found on the Desktop."
  echo "Take one with Cmd+Shift+4, then run this again."
  exit 1
fi

# Sequence number = however many are already filed, plus one.
n=$(find "$DEST" -name '[0-9][0-9]-*.png' | wc -l | tr -d ' ')
seq=$(printf "%02d" $((n + 1)))
target="$DEST/${seq}-${SLUG}.png"

mv "$latest" "$target"

[[ -f "$INDEX" ]] || echo "# Screenshot index" > "$INDEX"
echo "- \`${seq}-${SLUG}.png\` — ${DESC:-(no caption yet)} _(captured $(date '+%Y-%m-%d %H:%M'))_" >> "$INDEX"

echo "Filed: ${seq}-${SLUG}.png"
echo "From:  $(basename "$latest")"
