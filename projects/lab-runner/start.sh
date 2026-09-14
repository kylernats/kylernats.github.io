#!/usr/bin/env bash
# Start the local lab runner and open it.
cd "$(dirname "${BASH_SOURCE[0]}")"
( sleep 1; open "http://127.0.0.1:7878/?id=${1:-01-cost-visibility}" ) &
exec python3 server.py
