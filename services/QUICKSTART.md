# Quick Start Guide - I2C Internet Radio

Get your I2C-based internet radio up and running in 30 minutes!

## What You'll Need

### Hardware
- [ ] Raspberry Pi Zero 2 W (with power supply and microSD card)
- [ ] HiFiBerry MiniAmp (audio HAT)
- [ ] SparkFun Qwiic SHIM for Pi [ID:4463]
- [ ] Adafruit I2C Quad Rotary Encoder Breakout [ID:5752]
- [ ] 4× Rotary encoder knobs [ID:377]
- [ ] Monochrome 0.91" 128x32 OLED Display [ID:4440]
- [ ] 2× STEMMA QT cables (for daisy-chaining)
- [ ] Speaker (4-8Ω)

### Software
- Raspberry Pi OS Lite (or Full)
- Internet connection

## Step 1: Prepare Raspberry Pi (15 min)

1. **Flash Raspberry Pi OS** to microSD card using Raspberry Pi Imager
   - Choose: Raspberry Pi OS Lite (64-bit)
   - Configure WiFi and enable SSH in advanced options
   - Set hostname: `radio`

2. **Boot and SSH in**:
   ```bash
   ssh pi@radio.local
   # Default password: raspberry (change it!)
   ```

3. **Update system**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

4. **Enable I2C**:
   ```bash
   sudo raspi-config
   # Navigate: Interface Options → I2C → Yes
   ```

5. **Install required packages**:
   ```bash
   sudo apt install -y git mpd mpc i2c-tools python3-pip
   ```

6. **Reboot**:
   ```bash
   sudo reboot
   ```

## Step 2: Hardware Assembly (10 min)

1. **Install HiFiBerry MiniAmp**:
   - Attach to GPIO header (40-pin connector)
   - Connect speaker to screw terminals

2. **Install Qwiic SHIM**:
   - Place on top of HiFiBerry
   - Make sure GPIO pins align

3. **Connect Quad Encoder Breakout**:
   - Use STEMMA QT cable from SHIM to encoder breakout
   - Attach 4 encoder knobs to the breakout board

4. **Connect OLED Display**:
   - Use second STEMMA QT cable from encoder to OLED
   - This creates a daisy-chain: Pi → Encoder → OLED

5. **Verify connections**:
   ```bash
   i2cdetect -y 1
   ```
   
   You should see:
   - `49` (hex) = Quad Encoder Breakout
   - `3c` (hex) = OLED Display

## Step 3: Software Installation (5 min)

1. **Create radio user**:
   ```bash
   sudo useradd -m -s /bin/bash radio
   sudo usermod -a -G audio,i2c radio
   sudo passwd radio  # Set a password
   ```

2. **Clone repository** (as radio user):
   ```bash
   sudo -u radio bash
   cd ~
   git clone <your-repo-url> radio
   cd radio
   exit
   ```

3. **Run installer**:
   ```bash
   cd /home/radio/radio
   sudo ./install.sh
   ```

4. **Edit configuration**:
   ```bash
   sudo nano /home/radio/hardware-config.yaml
   ```
   
   Key settings to check:
   - `hifiberry_model: "miniamp"` (or "amp4")
   - I2C addresses (should be defaults: 0x49, 0x3C)
   - Volume limits
   - GitHub URL for stations.yaml

## Step 4: Configure HiFiBerry (5 min)

1. **Edit boot config**:
   ```bash
   sudo nano /boot/firmware/config.txt
   # Or on older systems: /boot/config.txt
   ```

2. **Add/modify**:
   ```
   # Disable onboard audio
   dtparam=audio=off
   
   # Enable HiFiBerry MiniAmp
   dtoverlay=hifiberry-dac
   ```

3. **Reboot**:
   ```bash
   sudo reboot
   ```

4. **Verify audio device**:
   ```bash
   aplay -l
   # Should show HiFiBerry device
   ```

## Step 5: Test Everything

### Test I2C Devices
```bash
i2cdetect -y 1
# Should show 49 and 3c
```

### Test Services
```bash
sudo systemctl status encoder-controller
sudo systemctl status oled-display
sudo systemctl status shuffle-mode
```

### Test Encoders
1. Turn Encoder 1 → Should cycle banks (watch OLED)
2. Turn Encoder 2 → Should cycle stations
3. Turn Encoder 3 → Should change volume
4. Press buttons → Should trigger actions

### Test Audio
```bash
mpc status
# If nothing playing, start a station:
radio-play 0 0
```

## Quick Reference

### Control Scheme
| Encoder | Turn | Press |
|---------|------|-------|
| 1 (Bank) | Select bank 0-9 | Toggle shuffle |
| 2 (Station) | Select station 0-9 | Play/pause |
| 3 (Volume) | Adjust volume | Mute/unmute |
| 4 (Aux) | Not used | Not used |

### LED Colors
- **Encoder 1**: Bank color (red→orange→yellow→green→cyan→blue→purple→magenta)
- **Encoder 2**: Green=playing, Yellow=paused, Magenta=shuffle
- **Encoder 3**: Brightness shows volume level

### Useful Commands
```bash
# Play station
radio-play <bank> <station>

# Check status
radio-status

# View logs
sudo journalctl -u encoder-controller -f

# Restart services
sudo systemctl restart encoder-controller oled-display

# Check I2C devices
i2cdetect -y 1
```

## Troubleshooting

### No sound
1. Check HiFiBerry in `/boot/firmware/config.txt`
2. Verify speaker connection
3. Test: `speaker-test -t wav -c 1`
4. Check MPD: `sudo systemctl status mpd`

### OLED blank
1. Check I2C: `i2cdetect -y 1` (should show 3c)
2. Check service: `sudo systemctl status oled-display`
3. View logs: `sudo journalctl -u oled-display -f`

### Encoders not responding
1. Check I2C: `i2cdetect -y 1` (should show 49)
2. Check service: `sudo systemctl status encoder-controller`
3. View logs: `sudo journalctl -u encoder-controller -f`

### LEDs not working
1. Check config: `neopixels.enabled: true`
2. Restart service: `sudo systemctl restart encoder-controller`

## Customization

### Add Your Stations
Edit `/home/radio/stations.yaml`:
```yaml
banks:
  0:
    name: "My Stations"
    stations:
      0:
        name: "My Favorite Stream"
        type: stream
        url: "http://stream-url.com/radio.mp3"
```

### Change Colors
Edit `/home/radio/hardware-config.yaml`:
```yaml
neopixels:
  bank_colors:
    0: [255, 0, 0]    # Bank 0 = Red
    1: [0, 255, 0]    # Bank 1 = Green
    # ... customize all 10 banks
```

### Adjust Volume Limits
```yaml
volume:
  min: 20      # Don't go below 20%
  max: 80      # Don't go above 80%
  step: 5      # Change by 5% per click
```

## Next Steps

1. **Customize your stations** in `stations.yaml`
2. **Adjust colors** in `hardware-config.yaml`
3. **Set up auto-updates** from your GitHub repo
4. **Enable RSS feed** with nginx
5. **Add a case** for your radio

## Getting Help

- Review full README.md for detailed documentation
- Check MIGRATION_GUIDE.md if upgrading from GPIO version
- View logs: `sudo journalctl -u encoder-controller -f`
- Test I2C: `i2cdetect -y 1`

## Enjoy Your Radio! 🎵

Your internet radio is now ready! Turn the encoders, press buttons, and enjoy your favorite stations.

Happy listening! 📻
