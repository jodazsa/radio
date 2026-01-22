#!/usr/bin/env bash
set -euo pipefail

URL="https://raw.githubusercontent.com/jodazsa/radio/refs/heads/main/config/stations.yaml"
OUT="/home/radio/stations.yaml"
TMP="$(mktemp)"

curl -fsSL "$URL" -o "$TMP"

# Basic sanity check: must contain "banks:"
grep -q "^banks:" "$TMP"

install -m 0644 "$TMP" "$OUT"
rm -f "$TMP"

echo "Stations updated successfully from GitHub"
