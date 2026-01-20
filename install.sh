#!/bin/bash
# install.sh - Install/update radio scripts and config from GitHub

REPO_DIR="/home/radio/radio"
SCRIPT_NAME="radio-play"

echo "Getting updated files from GitHub..."

# Pull latest changes
cd $REPO_DIR
git pull

# Install script to system-wide location
echo "Installing $SCRIPT_NAME..."
sudo cp scripts/$SCRIPT_NAME /usr/local/bin/
sudo chmod +x /usr/local/bin/$SCRIPT_NAME

# Copy config to home directory
echo "Updating stations.yaml..."
cp config/stations.yaml /home/radio/stations.yaml

echo ""
echo "Updated successfully!"
echo ""
echo "Usage: radio-play <bank> <station>"
echo "Example: radio-play 0 0"
