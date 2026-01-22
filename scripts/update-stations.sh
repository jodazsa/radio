#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="/home/radio/hardware-config.yaml"

# Read configuration using Python
read_config() {
    python3 - <<EOF
import yaml
try:
    with open('$CONFIG_FILE') as f:
        config = yaml.safe_load(f)
    print(config['auto_update']['github_url'])
    print(config['paths']['stations_yaml'])
    print(config['auto_update'].get('enabled', True))
except Exception as e:
    # Fallback to defaults
    print("https://raw.githubusercontent.com/jodazsa/radio/refs/heads/main/config/stations.yaml")
    print("/home/radio/stations.yaml")
    print("True")
EOF
}

# Read config values into array
IFS=$'\n' read -d '' -r -a config_values < <(read_config) || true

URL="${config_values[0]}"
OUT="${config_values[1]}"
ENABLED="${config_values[2]}"

# Check if auto-update is enabled
if [ "$ENABLED" != "True" ]; then
    echo "Auto-update is disabled in config"
    exit 0
fi

echo "Updating stations from: $URL"
echo "Saving to: $OUT"

TMP="$(mktemp)"

curl -fsSL "$URL" -o "$TMP"

# Basic sanity check: must contain "banks:"
grep -q "^banks:" "$TMP"

install -m 0644 "$TMP" "$OUT"
rm -f "$TMP"

echo "Stations updated successfully from GitHub"
