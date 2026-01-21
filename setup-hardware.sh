#!/bin/bash
# setup-hardware.sh - Configure Raspberry Pi for radio based on hardware-config.yaml

CONFIG_FILE="/home/radio/hardware-config.yaml"
BOOT_CONFIG="/boot/firmware/config.txt"

echo "Radio Hardware Setup Script"
echo "============================"
echo ""

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: $CONFIG_FILE not found!"
    echo "Please copy hardware-config.yaml to /home/radio/ and customize it."
    exit 1
fi

# Parse YAML (simple approach - requires python3-yaml)
HIFIBERRY_MODEL=$(python3 << EOF
import yaml
with open('$CONFIG_FILE') as f:
    config = yaml.safe_load(f)
print(config['hifiberry_model'])
EOF
)

OVERLAY=$(python3 << EOF
import yaml
with open('$CONFIG_FILE') as f:
    config = yaml.safe_load(f)
print(config['hifiberry_configs']['$HIFIBERRY_MODEL']['overlay'])
EOF
)

echo "Detected HiFiBerry model: $HIFIBERRY_MODEL"
echo "Using overlay: $OVERLAY"
echo ""

# Backup boot config
echo "Backing up boot config..."
sudo cp $BOOT_CONFIG ${BOOT_CONFIG}.backup

# Check if HiFiBerry overlay is already configured
if grep -q "^dtoverlay=hifiberry" $BOOT_CONFIG; then
    echo "Updating existing HiFiBerry overlay..."
    sudo sed -i "s/^dtoverlay=hifiberry.*/dtoverlay=$OVERLAY/" $BOOT_CONFIG
else
    echo "Adding HiFiBerry overlay..."
    # Comment out default audio
    sudo sed -i 's/^dtparam=audio=on/#dtparam=audio=on/' $BOOT_CONFIG
    # Add HiFiBerry overlay
    echo "dtoverlay=$OVERLAY" | sudo tee -a $BOOT_CONFIG
fi

echo ""
echo "✓ Boot configuration updated"
echo ""

# Configure MPD audio output
echo "Configuring MPD..."

MONO_DOWNMIX=$(python3 << EOF
import yaml
with open('$CONFIG_FILE') as f:
    config = yaml.safe_load(f)
print('true' if config['audio_processing']['mono_downmix'] else 'false')
EOF
)

AUDIO_FORMAT=$(python3 << EOF
import yaml
with open('$CONFIG_FILE') as f:
    config = yaml.safe_load(f)
print(config['audio_processing']['format'])
EOF
)

CARD=$(python3 << EOF
import yaml
with open('$CONFIG_FILE') as f:
    config = yaml.safe_load(f)
print(config['audio']['card'])
EOF
)

DEVICE=$(python3 << EOF
import yaml
with open('$CONFIG_FILE') as f:
    config = yaml.safe_load(f)
print(config['audio']['device'])
EOF
)

# Generate MPD audio_output config
cat > /tmp/mpd_audio_output.conf << MPDCONF
audio_output {
    type        "alsa"
    name        "HiFiBerry"
    device      "hw:$CARD,$DEVICE"
    mixer_type  "software"
MPDCONF

if [ "$MONO_DOWNMIX" = "true" ]; then
    echo "    format      \"$AUDIO_FORMAT\"" >> /tmp/mpd_audio_output.conf
fi

echo "}" >> /tmp/mpd_audio_output.conf

echo "MPD audio output configuration:"
cat /tmp/mpd_audio_output.conf
echo ""
echo "Note: You'll need to manually update /etc/mpd.conf with the above configuration"
echo "      (We don't auto-edit mpd.conf to avoid breaking existing configs)"
echo ""

# Show GPIO assignments
echo "GPIO Pin Assignments:"
python3 << EOF
import yaml
with open('$CONFIG_FILE') as f:
    config = yaml.safe_load(f)
    
reserved = config['hifiberry_configs']['$HIFIBERRY_MODEL']['reserved_gpios']
print(f"Reserved by HiFiBerry: {reserved}")
print("")
print("Station Switch:")
for bit, pin in config['gpio']['station_switch'].items():
    print(f"  {bit}: GPIO {pin}")
print("")
print("Bank Switch:")
for bit, pin in config['gpio']['bank_switch'].items():
    print(f"  {bit}: GPIO {pin}")
print("")
print("Encoder I2C Address: 0x{:02x}".format(config['gpio']['encoder_i2c_address']))
EOF

echo ""
echo "✓ Hardware setup complete!"
echo ""
echo "Next steps:"
echo "1. Review /etc/mpd.conf and update audio_output section with config shown above"
echo "2. Reboot the Pi: sudo reboot"
echo "3. Run install.sh to install radio scripts"
echo ""
