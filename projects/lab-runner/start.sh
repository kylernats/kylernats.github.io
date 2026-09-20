#!/usr/bin/env bash
# Start the lab runner and open it. Also refreshes the standalone guide.
#
#   ./projects/lab-runner/start.sh              # lab 01
#   ./projects/lab-runner/start.sh 02-backup    # a different lab

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
LAB="${1:-01-cost-visibility}"

# Refresh the offline guide so the double-click copy is never stale.
python3 export-guide.py "$LAB" >/dev/null 2>&1 || true
python3 build-walkthrough.py "$LAB" >/dev/null 2>&1 || true

( sleep 1; open "http://127.0.0.1:7878/?id=$LAB" ) &
echo "  Watch first: http://127.0.0.1:7878/watch?id=$LAB"
echo "  Lab runner : http://127.0.0.1:7878/?id=$LAB"
echo "  Full guide : http://127.0.0.1:7878/guide?id=$LAB"
echo "  Offline    : ../$LAB/docs/guide.html  (works with the server off)"
echo
exec python3 server.py
