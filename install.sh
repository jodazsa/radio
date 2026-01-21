#!/bin/bash
# install.sh - Install/update radio scripts and config from GitHub

REPO_DIR="/home/radio/radio"
SCRIPT_NAME="radio-play"
VOLUME_SCRIPT="volume-control"
SELECTOR_SCRIPT="station-selector"

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

# Copy config to home directory
echo "Updating stations.yaml..."
cp config/stations.yaml /home/radio/stations.yaml

echo ""
echo "✓ Radio setup updated successfully!"
echo ""
echo "Usage: radio-play <bank> <station>"
echo "Example: radio-play 0 0"
echo ""
echo "Services running:"
echo "  - volume-control (rotary encoder)"
echo "  - station-selector (BCD switch)"
echo ""
echo "Check status:"
echo "  sudo systemctl status volume-control"
echo "  sudo systemctl status station-selector"
