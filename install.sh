#!/bin/bash
# install.sh - Install/update radio scripts and config from GitHub

REPO_DIR="/home/radio/radio"
SCRIPT_NAME="radio-play"
VOLUME_SCRIPT="volume-control"
SELECTOR_SCRIPT="station-selector"
STATUS_SCRIPT="radio-status"
UPDATE_SCRIPT="update-stations.sh"
DISPLAY_SCRIPT="station-display"
SHUFFLE_SCRIPT="shuffle-mode"

echo "Updating radio setup from GitHub..."

# Pull latest changes
cd $REPO_DIR
git pull

# Install scripts to system-wide location
echo "Installing $SCRIPT_NAME..."
sudo cp scripts/$SCRIPT_NAME /usr/local/bin/
sudo chmod +x /usr/local/bin/$SCRIPT_NAME

echo "Installing $VOLUME_SCRIPT..."
sudo cp scripts/$VOLUME_SCRIPT /usr/local/bin/
sudo chmod +x /usr/local/bin/$VOLUME_SCRIPT

echo "Installing $SELECTOR_SCRIPT..."
sudo cp scripts/$SELECTOR_SCRIPT /usr/local/bin/
sudo chmod +x /usr/local/bin/$SELECTOR_SCRIPT

echo "Installing $STATUS_SCRIPT..."
sudo cp scripts/$STATUS_SCRIPT /usr/local/bin/
sudo chmod +x /usr/local/bin/$STATUS_SCRIPT

echo "Installing $DISPLAY_SCRIPT..."
sudo cp scripts/$DISPLAY_SCRIPT /usr/local/bin/
sudo chmod +x /usr/local/bin/$DISPLAY_SCRIPT

echo "Installing display server..."
sudo cp scripts/display-server /usr/local/bin/
sudo chmod +x /usr/local/bin/display-server
sudo cp config/display.html /usr/local/share/radio-display.html

echo "Installing RSS generator..."
sudo cp scripts/rss-generator /usr/local/bin/
sudo chmod +x /usr/local/bin/rss-generator

echo "Installing $SHUFFLE_SCRIPT..."
sudo cp scripts/$SHUFFLE_SCRIPT /usr/local/bin/
sudo chmod +x /usr/local/bin/$SHUFFLE_SCRIPT

# Make sure update script is executable
chmod +x scripts/$UPDATE_SCRIPT

# Install systemd services
echo "Installing volume control service..."
sudo cp services/volume-control.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable volume-control.service
sudo systemctl restart volume-control.service

echo "Installing station selector service..."
sudo cp services/station-selector.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable station-selector.service
sudo systemctl restart station-selector.service

echo "Installing shuffle mode service..."
sudo cp services/shuffle-mode.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable shuffle-mode.service
sudo systemctl restart shuffle-mode.service

echo "Installing auto-update timer..."
sudo cp services/radio-update-stations.service /etc/systemd/system/
sudo cp services/radio-update-stations.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable radio-update-stations.timer
sudo systemctl start radio-update-stations.timer

echo "Installing station display service (optional - for HDMI displays)..."
sudo cp services/station-display.service /etc/systemd/system/
sudo cp services/display-server.service /etc/systemd/system/
sudo cp services/display-browser.service /etc/systemd/system/
sudo systemctl daemon-reload
# Don't enable by default - user can enable if they have a display
echo "Note: To enable display, run:"
echo "  sudo systemctl enable --now display-server"
echo "  sudo systemctl enable --now display-browser"

echo "Installing RSS generator service..."
sudo cp services/rss-generator.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rss-generator.service
sudo systemctl restart rss-generator.service
echo "RSS feed will be available at http://[pi-ip-address]/radio.rss"

# Copy config to home directory
echo "Updating stations.yaml..."
cp config/stations.yaml /home/radio/stations.yaml

# Copy hardware-config.yaml if it doesn't exist (don't overwrite existing)
if [ ! -f /home/radio/hardware-config.yaml ]; then
    echo "Installing default hardware-config.yaml..."
    cp config/hardware-config.yaml /home/radio/hardware-config.yaml
    echo "⚠ Please edit /home/radio/hardware-config.yaml to match your hardware setup"
else
    echo "hardware-config.yaml already exists, not overwriting"
fi

echo ""
echo "✓ Radio setup updated successfully!"
echo ""
echo "Commands:"
echo "  radio-play <bank> <station>  - Play a station"
echo "  radio-status                 - Show current station"
echo ""
echo "Services running:"
echo "  - volume-control (rotary encoder)"
echo "  - station-selector (BCD switch)"
echo "  - shuffle-mode (shuffle switch)"
echo "  - radio-update-stations.timer (daily YAML updates)"
echo ""
echo "Check status:"
echo "  sudo systemctl status volume-control"
echo "  sudo systemctl status station-selector"
echo "  sudo systemctl status shuffle-mode"
echo "  sudo systemctl list-timers radio-update-stations.timer"
