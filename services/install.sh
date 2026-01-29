#!/bin/bash
# install.sh - Install/update radio scripts and config for I2C hardware

REPO_DIR="/home/radio/radio"
SCRIPT_NAME="radio-play"
ENCODER_SCRIPT="encoder-controller"
DISPLAY_SCRIPT="oled-display"
STATUS_SCRIPT="radio-status"
UPDATE_SCRIPT="update-stations.sh"
SHUFFLE_SCRIPT="shuffle-mode"
RSS_SCRIPT="rss-generator"

echo "=========================================="
echo "Internet Radio - I2C Edition Installer"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Error: This script must be run with sudo"
    echo "Usage: sudo ./install.sh"
    exit 1
fi

echo "Step 1: Updating repository..."
if [ -d "$REPO_DIR" ]; then
    cd $REPO_DIR
    git pull
else
    echo "Warning: Repository directory not found at $REPO_DIR"
    echo "Proceeding with local files..."
fi

echo ""
echo "Step 2: Installing Python dependencies..."

# Install Adafruit libraries for I2C devices
pip3 install --break-system-packages \
    adafruit-circuitpython-seesaw \
    adafruit-circuitpython-ssd1306 \
    adafruit-blinka \
    Pillow \
    PyYAML

echo ""
echo "Step 3: Installing scripts to /usr/local/bin/..."

# Install scripts
install_script() {
    local script=$1
    echo "  Installing $script..."
    cp scripts/$script /usr/local/bin/
    chmod +x /usr/local/bin/$script
}

install_script $SCRIPT_NAME
install_script $ENCODER_SCRIPT
install_script $DISPLAY_SCRIPT
install_script $STATUS_SCRIPT
install_script $SHUFFLE_SCRIPT
install_script $RSS_SCRIPT

# Make update script executable
chmod +x scripts/$UPDATE_SCRIPT

echo ""
echo "Step 4: Installing systemd services..."

# Install service files
install_service() {
    local service=$1
    echo "  Installing $service..."
    cp services/$service /etc/systemd/system/
}

install_service encoder-controller.service
install_service oled-display.service
install_service shuffle-mode.service
install_service rss-generator.service
install_service radio-update-stations.service
install_service radio-update-stations.timer

# Reload systemd
systemctl daemon-reload

echo ""
echo "Step 5: Enabling and starting services..."

# Enable and start encoder controller
echo "  Enabling encoder-controller..."
systemctl enable encoder-controller.service
systemctl restart encoder-controller.service

# Enable and start OLED display
echo "  Enabling oled-display..."
systemctl enable oled-display.service
systemctl restart oled-display.service

# Enable and start shuffle mode
echo "  Enabling shuffle-mode..."
systemctl enable shuffle-mode.service
systemctl restart shuffle-mode.service

# Enable and start RSS generator
echo "  Enabling rss-generator..."
systemctl enable rss-generator.service
systemctl restart rss-generator.service

# Enable and start auto-update timer
echo "  Enabling auto-update timer..."
systemctl enable radio-update-stations.timer
systemctl start radio-update-stations.timer

echo ""
echo "Step 6: Setting up configuration files..."

# Copy stations.yaml
if [ ! -f /home/radio/stations.yaml ]; then
    echo "  Installing default stations.yaml..."
    cp config/stations.yaml /home/radio/stations.yaml
    chown radio:radio /home/radio/stations.yaml
else
    echo "  stations.yaml already exists, not overwriting"
fi

# Copy hardware-config.yaml if it doesn't exist
if [ ! -f /home/radio/hardware-config.yaml ]; then
    echo "  Installing default hardware-config.yaml..."
    cp config/hardware-config.yaml /home/radio/hardware-config.yaml
    chown radio:radio /home/radio/hardware-config.yaml
    echo ""
    echo "⚠️  IMPORTANT: Edit /home/radio/hardware-config.yaml to match your setup!"
else
    echo "  hardware-config.yaml already exists, not overwriting"
    echo ""
    echo "⚠️  Note: The I2C hardware uses a different configuration format."
    echo "    You may want to review and update your hardware-config.yaml"
fi

# Create audio directory if it doesn't exist
if [ ! -d /home/radio/audio ]; then
    mkdir -p /home/radio/audio
    chown radio:radio /home/radio/audio
    echo "  Created /home/radio/audio directory"
fi

# Set proper ownership
chown -R radio:radio /home/radio/

echo ""
echo "Step 7: Checking I2C configuration..."

# Check if I2C is enabled
if [ -e /dev/i2c-1 ]; then
    echo "  ✓ I2C is enabled"
    
    # Check if radio user is in i2c group
    if groups radio | grep -q "\bi2c\b"; then
        echo "  ✓ User 'radio' is in i2c group"
    else
        echo "  Adding user 'radio' to i2c group..."
        usermod -a -G i2c radio
        echo "  ✓ User added to i2c group"
    fi
else
    echo "  ⚠️  I2C does not appear to be enabled!"
    echo ""
    echo "To enable I2C:"
    echo "  1. Run: sudo raspi-config"
    echo "  2. Select: Interface Options → I2C → Enable"
    echo "  3. Reboot"
    echo ""
fi

# Detect I2C devices
echo ""
echo "  Scanning I2C bus for devices..."
if command -v i2cdetect &> /dev/null; then
    i2cdetect -y 1
    echo ""
    echo "  Expected devices:"
    echo "    0x49 - Quad Rotary Encoder Breakout"
    echo "    0x3C - SSD1306 OLED Display"
else
    echo "  i2cdetect not found. Install with: sudo apt-get install i2c-tools"
fi

echo ""
echo "=========================================="
echo "✓ Installation complete!"
echo "=========================================="
echo ""
echo "Hardware Setup:"
echo "  - Connect Quad Encoder Breakout to I2C (default: 0x49)"
echo "  - Connect OLED Display to I2C (default: 0x3C)"
echo "  - Use STEMMA QT cables to daisy-chain devices"
echo "  - Connect to Raspberry Pi via Qwiic SHIM"
echo ""
echo "Commands:"
echo "  radio-play <bank> <station>  - Play a station"
echo "  radio-status                 - Show current station"
echo ""
echo "Services running:"
echo "  - encoder-controller (quad rotary encoder + NeoPixels)"
echo "  - oled-display (128x32 I2C OLED)"
echo "  - shuffle-mode (automatic station shuffling)"
echo "  - rss-generator (RSS feed)"
echo "  - radio-update-stations.timer (daily YAML updates)"
echo ""
echo "Check status:"
echo "  sudo systemctl status encoder-controller"
echo "  sudo systemctl status oled-display"
echo "  sudo systemctl status shuffle-mode"
echo "  sudo journalctl -u encoder-controller -f   # Live logs"
echo ""
echo "RSS feed available at: http://[pi-ip-address]/radio.rss"
echo ""
echo "Control Scheme:"
echo "  Encoder 1: Bank selection (turn) | Toggle shuffle (press)"
echo "  Encoder 2: Station selection (turn) | Play/pause (press)"
echo "  Encoder 3: Volume (turn) | Mute/unmute (press)"
echo "  Encoder 4: Reserved for future use"
echo ""
