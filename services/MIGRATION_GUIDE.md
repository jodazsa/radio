# Migration Guide: GPIO BCD Switches → I2C Encoders

This guide will help you migrate from the GPIO-based BCD rotary switches to the new I2C-based quad encoder system.

## Overview of Changes

### Hardware Changes
| Component | Old | New |
|-----------|-----|-----|
| Bank Selection | FR01AR10PB BCD Switch (4 GPIO pins) | Encoder 1 on Quad Breakout (I2C) |
| Station Selection | FR01AR10PB BCD Switch (4 GPIO pins) | Encoder 2 on Quad Breakout (I2C) |
| Volume Control | Adafruit I2C Encoder @ 0x36 | Encoder 3 on Quad Breakout (I2C @ 0x49) |
| Display | None | 128x32 OLED @ 0x3C |
| Visual Feedback | None | 4× NeoPixel LEDs on encoders |
| Total GPIO Pins Used | 8 pins | 0 pins (I2C only: SDA, SCL) |

### Software Changes
| Component | Old | New |
|-----------|-----|-----|
| station-selector | Read GPIO pins | Read I2C encoder |
| volume-control | Separate service | Merged into encoder-controller |
| shuffle-mode | GPIO switch | Button press, state file |
| Display | None | New oled-display service |
| Dependencies | RPi.GPIO | adafruit-circuitpython libraries |

## Migration Steps

### Step 1: Backup Everything

```bash
# Backup configuration
cp /home/radio/hardware-config.yaml ~/hardware-config.yaml.backup
cp /home/radio/stations.yaml ~/stations.yaml.backup
cp /home/radio/.radio-state ~/radio-state.backup

# Backup service logs if needed
sudo journalctl -u station-selector > ~/station-selector.log
sudo journalctl -u volume-control > ~/volume-control.log
```

### Step 2: Stop Old Services

```bash
# Stop all old services
sudo systemctl stop station-selector.service
sudo systemctl stop volume-control.service
sudo systemctl stop shuffle-mode.service

# Disable them so they don't restart
sudo systemctl disable station-selector.service
sudo systemctl disable volume-control.service
sudo systemctl disable shuffle-mode.service
```

### Step 3: Physical Hardware Changes

1. **Disconnect old hardware**:
   - Remove BCD switches from GPIO pins
   - Remove old I2C encoder if using different address
   - Keep HiFiBerry MiniAmp connected (it stays the same)

2. **Install new hardware**:
   - Attach SparkFun Qwiic SHIM to GPIO header
   - Connect Quad Encoder Breakout via STEMMA QT cable
   - Daisy-chain OLED Display to Quad Encoder
   - Attach physical encoder knobs to breakout board

3. **Verify I2C connections**:
   ```bash
   i2cdetect -y 1
   ```
   
   You should see:
   ```
        0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
   00:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
   10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
   20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
   30: -- -- -- -- -- -- -- -- -- -- -- -- 3c -- -- -- 
   40: -- -- -- -- -- -- -- -- -- 49 -- -- -- -- -- -- 
   50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
   60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
   70: -- -- -- -- -- -- -- --
   ```
   - `3c` = OLED Display
   - `49` = Quad Encoder Breakout

### Step 4: Update Repository

```bash
cd /home/radio/radio
git pull  # Or clone the new version
# If you have the I2C version in a separate branch/repo:
# git checkout i2c-edition
```

### Step 5: Run New Installer

```bash
cd /home/radio/radio
sudo ./install.sh
```

This will:
- Install new Python dependencies
- Copy new scripts
- Install new systemd services
- Enable and start services

### Step 6: Update Configuration

The new `hardware-config.yaml` has a different structure. You'll need to manually merge your settings.

**Old configuration** (GPIO pins):
```yaml
gpio:
  encoder_i2c_address: 0x36
  station_switch:
    bit0: 10
    bit1: 9
    bit2: 22
    bit3: 17
  bank_switch:
    bit0: 5
    bit1: 6
    bit2: 13
    bit3: 11
  shuffle_switch: 24
```

**New configuration** (I2C addresses):
```yaml
i2c:
  encoder_i2c_address: 0x49  # Quad encoder breakout
  oled_i2c_address: 0x3C     # OLED display
  oled_width: 128
  oled_height: 32

encoders:
  bank_encoder: 0      # Which encoder is bank
  station_encoder: 1   # Which encoder is station
  volume_encoder: 2    # Which encoder is volume
  aux_encoder: 3       # Extra encoder (unused)

button_actions:
  bank_button: "toggle_shuffle"   # Replaces GPIO switch
  station_button: "play_pause"
  volume_button: "mute_toggle"
```

**Settings to preserve**:
```yaml
# These stay the same
volume:
  min: 0
  max: 100
  default: 50
  step: 4

shuffle_mode:
  interval_seconds: 45
  enabled_banks: [0, 1, 2, 3, 4, 5, 6, 7]

auto_update:
  github_url: "your-github-url"
  enabled: true
```

### Step 7: Restore stations.yaml

```bash
# If you have custom stations, restore them
cp ~/stations.yaml.backup /home/radio/stations.yaml
sudo chown radio:radio /home/radio/stations.yaml
```

### Step 8: Test the System

1. **Check services are running**:
   ```bash
   sudo systemctl status encoder-controller
   sudo systemctl status oled-display
   sudo systemctl status shuffle-mode
   ```

2. **Test encoders**:
   - Turn Encoder 1: Should cycle through banks
   - Turn Encoder 2: Should cycle through stations
   - Turn Encoder 3: Should adjust volume
   - Press buttons: Should trigger actions

3. **Check OLED display**:
   - Should show current bank and station
   - Should update when you change selection
   - Should show playback metadata

4. **Check NeoPixels**:
   - Each encoder should have a colored LED
   - Colors should change based on state

5. **Test playback**:
   ```bash
   mpc status
   # Should show current station playing
   ```

### Step 9: Monitor for Issues

```bash
# Watch encoder controller logs
sudo journalctl -u encoder-controller -f

# Watch OLED display logs
sudo journalctl -u oled-display -f

# Check for errors
sudo journalctl -u encoder-controller --since "5 minutes ago" | grep -i error
```

## Common Migration Issues

### Issue: I2C devices not detected

**Symptom**: `i2cdetect` doesn't show devices at 0x49 or 0x3C

**Solutions**:
1. Check physical connections
2. Try different STEMMA QT cables
3. Verify I2C is enabled: `sudo raspi-config`
4. Check for I2C conflicts with old setup

### Issue: Services won't start

**Symptom**: `systemctl status` shows failed services

**Solutions**:
1. Check logs: `sudo journalctl -u encoder-controller -n 50`
2. Verify Python libraries installed: `pip3 list | grep adafruit`
3. Check permissions: `groups radio` should include `i2c`
4. Manually test: `sudo -u radio /usr/local/bin/encoder-controller`

### Issue: Encoders respond backwards

**Symptom**: Turning encoder clockwise decreases value

**Solutions**:
1. This is a library/hardware characteristic
2. Can be fixed in code if needed (swap encoder pins in configuration)

### Issue: Old services interfering

**Symptom**: Both old and new services trying to control radio

**Solutions**:
```bash
# Make sure old services are fully disabled
sudo systemctl disable station-selector
sudo systemctl disable volume-control
sudo systemctl stop station-selector
sudo systemctl stop volume-control

# Mask them to prevent any restart
sudo systemctl mask station-selector
sudo systemctl mask volume-control
```

### Issue: Volume not working

**Symptom**: Encoder turns but volume doesn't change

**Solutions**:
1. Check MPD is running: `sudo systemctl status mpd`
2. Test volume manually: `mpc volume 75`
3. Check ALSA card: `aplay -l`
4. Verify HiFiBerry configuration in `/boot/config.txt`

### Issue: Display shows garbage or is blank

**Symptom**: OLED has random pixels or shows nothing

**Solutions**:
1. Check I2C address: Should be 0x3C for SSD1306
2. Verify display dimensions in config: 128x32
3. Test with simple script:
   ```python
   import board
   import busio
   import adafruit_ssd1306
   i2c = busio.I2C(board.SCL, board.SDA)
   display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, addr=0x3C)
   display.fill(1)
   display.show()
   ```

## Reverting to Old System

If you need to roll back:

1. **Stop new services**:
   ```bash
   sudo systemctl stop encoder-controller oled-display
   sudo systemctl disable encoder-controller oled-display
   ```

2. **Restore old services**:
   ```bash
   sudo systemctl unmask station-selector volume-control
   sudo systemctl enable station-selector volume-control
   sudo systemctl start station-selector volume-control
   ```

3. **Restore old configuration**:
   ```bash
   cp ~/hardware-config.yaml.backup /home/radio/hardware-config.yaml
   cp ~/stations.yaml.backup /home/radio/stations.yaml
   ```

4. **Reconnect old hardware** (BCD switches to GPIO pins)

## Configuration Comparison

### Before (GPIO):
```yaml
gpio:
  encoder_i2c_address: 0x36
  shuffle_switch: 24
  station_switch:
    bit0: 10
    bit1: 9
    bit2: 22
    bit3: 17
  bank_switch:
    bit0: 5
    bit1: 6
    bit2: 13
    bit3: 11
```

### After (I2C):
```yaml
i2c:
  encoder_i2c_address: 0x49
  oled_i2c_address: 0x3C

encoders:
  bank_encoder: 0
  station_encoder: 1
  volume_encoder: 2
  aux_encoder: 3

button_actions:
  bank_button: "toggle_shuffle"
  station_button: "play_pause"
  volume_button: "mute_toggle"
```

## Benefits of New System

1. **Fewer wires**: I2C daisy-chain vs 8 GPIO pins
2. **More features**: OLED display, NeoPixels
3. **Easier assembly**: STEMMA QT connectors, no soldering
4. **Better feedback**: Visual display and colored LEDs
5. **Expandable**: I2C bus supports many more devices
6. **Cleaner code**: Single service vs multiple GPIO readers

## Additional Resources

- **Adafruit Seesaw Guide**: https://learn.adafruit.com/adafruit-i2c-qt-rotary-encoder
- **SSD1306 OLED Guide**: https://learn.adafruit.com/monochrome-oled-breakouts
- **I2C Troubleshooting**: https://learn.adafruit.com/circuitpython-essentials/circuitpython-i2c

## Questions?

If you encounter issues not covered here:

1. Check system logs: `sudo journalctl -u encoder-controller -f`
2. Verify I2C bus: `i2cdetect -y 1`
3. Test components individually
4. Review README.md for detailed troubleshooting
