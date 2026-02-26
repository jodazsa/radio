#!/bin/bash
# install.sh — One-time setup for simplified Pi radio
set -e

echo "=== Simplified Pi Radio — Install ==="
echo ""

if [ "$EUID" -eq 0 ]; then
    echo "Please run as regular user, not root."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 1. System packages
echo "→ Updating system and installing packages..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y mpd mpc python3-pip python3-yaml python3-rpi.gpio i2c-tools

# 2. Enable I2C
echo "→ Enabling I2C..."
sudo raspi-config nonint do_i2c 0

# 3. HiFiBerry DAC
echo "→ Configuring HiFiBerry DAC..."
if [ -f /boot/firmware/config.txt ]; then
    CONFIG_FILE="/boot/firmware/config.txt"
elif [ -f /boot/config.txt ]; then
    CONFIG_FILE="/boot/config.txt"
else
    echo "WARNING: Boot config not found, skipping DAC setup"
    CONFIG_FILE=""
fi

if [ -n "$CONFIG_FILE" ]; then
    grep -q "dtoverlay=hifiberry-dac" "$CONFIG_FILE" \
        || echo "dtoverlay=hifiberry-dac" | sudo tee -a "$CONFIG_FILE"
    sudo sed -i 's/^dtparam=audio=on/#dtparam=audio=on/' "$CONFIG_FILE" 2>/dev/null || true
fi

# 4. Python libraries (Seesaw for I2C encoder)
echo "→ Installing Python libraries..."
pip3 install --break-system-packages Adafruit-Blinka adafruit-circuitpython-seesaw

# 5. Create radio user and directories
echo "→ Setting up radio user..."
id -u radio &>/dev/null || sudo useradd -m -s /bin/bash radio
sudo usermod -aG audio,i2c,gpio radio
sudo mkdir -p /home/radio/audio /home/radio/logs
sudo chmod 755 /home/radio /home/radio/audio /home/radio/logs

# 6. Install radio files
echo "→ Installing radio files..."
sudo cp "$SCRIPT_DIR/radio.py" /usr/local/bin/radio.py
sudo chmod +x /usr/local/bin/radio.py

# Copy stations.yaml only if not already present (don't overwrite edits)
if [ ! -f /home/radio/stations.yaml ]; then
    sudo cp "$SCRIPT_DIR/stations.yaml" /home/radio/stations.yaml
    sudo chown radio:radio /home/radio/stations.yaml
    echo "  Installed default stations.yaml"
else
    echo "  stations.yaml already exists, keeping your version"
fi

# 7. Configure MPD
echo "→ Configuring MPD..."
sudo tee /etc/mpd.conf > /dev/null << 'MPDCONF'
music_directory     "/home/radio/audio"
playlist_directory  "/var/lib/mpd/playlists"
db_file             "/var/lib/mpd/tag_cache"
log_file            "/var/log/mpd/mpd.log"
pid_file            "/run/mpd/pid"
state_file          "/var/lib/mpd/state"
sticker_file        "/var/lib/mpd/sticker.sql"

bind_to_address     "localhost"
port                "6600"

auto_update         "yes"

input {
    plugin "curl"
}

audio_output {
    type        "alsa"
    name        "HiFiBerry DAC"
    mixer_type  "software"
}
MPDCONF

sudo systemctl restart mpd
sudo systemctl enable mpd

# 8. Install systemd service
echo "→ Installing radio service..."
sudo cp "$SCRIPT_DIR/radio.service" /etc/systemd/system/radio.service
sudo systemctl daemon-reload
sudo systemctl enable radio
sudo systemctl start radio

echo ""
echo "=== Done! ==="
echo "Radio service is running. Reboot to apply DAC/I2C changes:"
echo "  sudo reboot"
echo ""
echo "After reboot, check status with:"
echo "  sudo systemctl status radio"
echo "  sudo journalctl -u radio -f"
