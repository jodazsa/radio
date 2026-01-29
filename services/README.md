# Raspberry Pi Internet Radio - I2C Edition

A complete internet radio system for Raspberry Pi Zero 2 W using I2C-based controls and display.

## Hardware Components

### Audio
- **Raspberry Pi Zero 2 W** - Main controller
- **HiFiBerry MiniAmp** - I2S audio HAT for speaker output

### I2C Devices (daisy-chained via STEMMA QT)
- **Adafruit I2C Quad Rotary Encoder Breakout** [ID:5752]
  - 4 rotary encoders with push buttons
  - 4 addressable NeoPixel RGB LEDs
  - I2C address: 0x49 (default)
  - Library: `adafruit-circuitpython-seesaw`

- **Monochrome 0.91" 128x32 I2C OLED Display** [ID:4440]
  - SSD1306 controller
  - I2C address: 0x3C (default)
  - Library: `adafruit-circuitpython-ssd1306`

- **SparkFun Qwiic SHIM for Pi** [ID:4463]
  - Provides Qwiic/STEMMA QT connector to Raspberry Pi GPIO
  - No soldering required

### Physical Encoders
- **4× Rotary Encoders** [ID:377] - The actual knobs that attach to the breakout

## Features

### Radio Control
- **100 Station Capacity**: 10 banks × 10 stations
- **Easy Navigation**: Dedicated encoders for bank and station selection
- **Volume Control**: Hardware encoder with configurable limits
- **Play/Pause**: Button press on station encoder
- **Shuffle Mode**: Automatic random station switching
- **Three Playback Types**:
  - Internet radio streams
  - Single MP3 files (with random seek position)
  - Directory playback (random start, sequential continuation)

### Visual Feedback
- **OLED Display**: Shows current bank, station, volume, and stream metadata
- **NeoPixel LEDs**:
  - Bank encoder: Color-coded by bank (0-9)
  - Station encoder: State indication (green=playing, yellow=paused, red=stopped)
  - Volume encoder: Brightness indicates volume level
  - Shuffle mode: Magenta color on station encoder

### System Features
- **Auto-Update**: Stations automatically update from GitHub repository
- **RSS Feed**: Real-time now-playing information
- **Persistent State**: Remembers last bank/station across reboots
- **Systemd Integration**: Reliable startup and monitoring
- **MPD Backend**: Professional-grade audio playback

## Control Scheme

### Encoder 1 (Bank Selection)
- **Turn**: Cycle through banks 0-9
- **Press**: Toggle shuffle mode on/off
- **LED**: Shows current bank color

### Encoder 2 (Station Selection)
- **Turn**: Select station 0-9 within current bank
- **Press**: Play/pause playback
- **LED**: Shows playback state or shuffle mode

### Encoder 3 (Volume Control)
- **Turn**: Adjust volume (respects min/max limits)
- **Press**: Mute/unmute
- **LED**: Brightness indicates volume level

### Encoder 4 (Reserved)
- Currently unused, available for future features

## OLED Display Layout

```
┌────────────────────────────────────┐
│ B3: Classical        [SHUFFLE]     │  ← Bank info
│ S5: BBC Radio 3                    │  ← Station info
│ ▶ V:75% ♪ Beethoven Symphony 9    │  ← Status + metadata
└────────────────────────────────────┘
```

## Installation

### Prerequisites

1. **Enable I2C**:
   ```bash
   sudo raspi-config
   # Interface Options → I2C → Enable
   ```

2. **Install I2C tools** (optional but helpful):
   ```bash
   sudo apt-get install i2c-tools
   ```

3. **Create radio user** (if not exists):
   ```bash
   sudo useradd -m -s /bin/bash radio
   sudo usermod -a -G audio,i2c radio
   ```

4. **Install MPD** (Music Player Daemon):
   ```bash
   sudo apt-get install mpd mpc
   ```

### Hardware Setup

1. **Connect the Qwiic SHIM** to Raspberry Pi GPIO header
2. **Connect devices via STEMMA QT cables**:
   - Pi → Quad Encoder Breakout
   - Quad Encoder → OLED Display
3. **Attach physical encoders** to the breakout board
4. **Connect HiFiBerry MiniAmp** to GPIO header (shares I2S pins)

### Software Installation

1. **Clone the repository**:
   ```bash
   cd /home/radio
   git clone <your-repo-url> radio
   cd radio
   ```

2. **Run installer**:
   ```bash
   sudo ./install.sh
   ```

3. **Edit configuration**:
   ```bash
   nano /home/radio/hardware-config.yaml
   # Adjust I2C addresses, volume limits, colors, etc.
   ```

4. **Verify I2C devices**:
   ```bash
   i2cdetect -y 1
   # Should show devices at 0x49 (encoder) and 0x3C (OLED)
   ```

## Configuration

### Hardware Configuration (`/home/radio/hardware-config.yaml`)

Key settings:
- **I2C addresses**: Encoder (0x49) and OLED (0x3C)
- **Volume limits**: Min/max/default/step
- **NeoPixel colors**: Customize bank and state colors
- **Encoder behavior**: Wrapping, button actions
- **Display settings**: Refresh rate, scrolling, what to show
- **Shuffle mode**: Interval, enabled banks

### Stations Configuration (`/home/radio/stations.yaml`)

Structure:
```yaml
banks:
  0:
    name: "Jazz"
    stations:
      0:
        name: "WWOZ New Orleans"
        type: stream
        url: "http://example.com/stream.mp3"
      1:
        name: "My Music Collection"
        type: mp3_dir_random_start_then_in_order
        dir: "jazz/collection"
```

Types:
- `stream`: Internet radio stream
- `mp3_loop_random_start`: Single file, random start, loops
- `mp3_dir_random_start_then_in_order`: Directory, random start file, sequential play

## Systemd Services

### Active Services
- `encoder-controller.service` - Monitors encoders and controls radio
- `oled-display.service` - Updates OLED with current info
- `shuffle-mode.service` - Handles automatic station shuffling
- `rss-generator.service` - Generates RSS feed
- `radio-update-stations.timer` - Auto-updates stations.yaml daily

### Service Management
```bash
# Check status
sudo systemctl status encoder-controller
sudo systemctl status oled-display

# View live logs
sudo journalctl -u encoder-controller -f

# Restart services
sudo systemctl restart encoder-controller
sudo systemctl restart oled-display

# Stop/start all radio services
sudo systemctl stop encoder-controller oled-display shuffle-mode
sudo systemctl start encoder-controller oled-display shuffle-mode
```

## Commands

```bash
# Play specific station
radio-play <bank> <station>
radio-play 3 5

# Check current status
radio-status

# Control MPD directly
mpc status
mpc volume 75
mpc pause
mpc play
```

## Troubleshooting

### I2C Devices Not Found

1. **Check physical connections**:
   - Ensure STEMMA QT cables are fully inserted
   - Try different cables if available
   - Check for loose connections

2. **Scan I2C bus**:
   ```bash
   i2cdetect -y 1
   ```

3. **Check I2C is enabled**:
   ```bash
   ls /dev/i2c-*
   # Should show /dev/i2c-1
   ```

4. **Verify permissions**:
   ```bash
   groups radio
   # Should include 'i2c' group
   ```

### Encoder Not Responding

1. **Check service status**:
   ```bash
   sudo systemctl status encoder-controller
   sudo journalctl -u encoder-controller -n 50
   ```

2. **Test I2C address**:
   ```bash
   i2cdetect -y 1
   # Should show 49 (or 0x49)
   ```

3. **Restart service**:
   ```bash
   sudo systemctl restart encoder-controller
   ```

### OLED Display Blank

1. **Check service status**:
   ```bash
   sudo systemctl status oled-display
   sudo journalctl -u oled-display -n 50
   ```

2. **Verify I2C address**:
   ```bash
   i2cdetect -y 1
   # Should show 3C (or 0x3C)
   ```

3. **Test manually**:
   ```bash
   sudo -u radio /usr/local/bin/oled-display
   ```

### NeoPixels Not Working

1. **Check configuration**:
   ```yaml
   neopixels:
     enabled: true  # Must be true
     brightness: 0.3
   ```

2. **Verify in logs**:
   ```bash
   sudo journalctl -u encoder-controller | grep -i neopixel
   ```

### Audio Issues

1. **Check MPD status**:
   ```bash
   sudo systemctl status mpd
   mpc status
   ```

2. **Test audio output**:
   ```bash
   speaker-test -t wav -c 1
   ```

3. **Verify HiFiBerry**:
   ```bash
   aplay -l
   # Should show HiFiBerry device
   ```

## Advanced Configuration

### Custom Bank Colors

Edit `/home/radio/hardware-config.yaml`:
```yaml
neopixels:
  bank_colors:
    0: [255, 0, 0]      # Red
    1: [255, 127, 0]    # Orange
    # ... customize as desired
```

### Adjust Shuffle Behavior

```yaml
shuffle_mode:
  interval_seconds: 30              # Change every 30 seconds
  enabled_banks: [0, 1, 2, 3]      # Only shuffle through first 4 banks
```

### Change Button Actions

```yaml
button_actions:
  bank_button: "toggle_shuffle"     # Default
  station_button: "play_pause"      # Default
  volume_button: "mute_toggle"      # Default
  aux_button: "none"                # Encoder 4
```

### Display Customization

```yaml
display:
  refresh_rate: 0.1                 # Update every 100ms
  scroll_enabled: true              # Scroll long text
  show_metadata: true               # Show song info
```

## RSS Feed

The system generates an RSS feed showing the currently playing station:

**URL**: `http://<pi-ip-address>/radio.rss`

### Setup RSS Web Server

1. **Install nginx**:
   ```bash
   sudo apt-get install nginx
   ```

2. **RSS file location**: `/var/www/html/radio.rss`

3. **Access**: Point any RSS reader to your Pi's IP

## Development

### State File Format

Located at `/home/radio/.radio-state`:
```
current_bank=3
current_station=5
volume=75
shuffle_enabled=false
shuffle_interval=45
last_update=2025-01-29T12:34:56
```

### Adding New Features

1. **Modify encoder-controller** for new controls
2. **Update hardware-config.yaml** with new settings
3. **Restart services** to apply changes

### Debugging

Enable debug logging in hardware-config.yaml:
```yaml
logging:
  enabled: true
  log_level: "DEBUG"
  log_file: "/home/radio/radio.log"
```

## Migrating from GPIO Version

If you're migrating from the GPIO-based BCD switch version:

1. **Backup your current configuration**:
   ```bash
   cp /home/radio/hardware-config.yaml ~/hardware-config.yaml.backup
   cp /home/radio/stations.yaml ~/stations.yaml.backup
   ```

2. **Stop old services**:
   ```bash
   sudo systemctl stop volume-control station-selector
   sudo systemctl disable volume-control station-selector
   ```

3. **Install new version**:
   ```bash
   cd /home/radio/radio
   git pull
   sudo ./install.sh
   ```

4. **Restore stations.yaml**:
   ```bash
   cp ~/stations.yaml.backup /home/radio/stations.yaml
   ```

5. **Update hardware-config.yaml** with I2C settings (manual merge required)

## Credits

- Hardware: Adafruit Industries, SparkFun Electronics
- Libraries: Adafruit CircuitPython, Python Pillow
- Audio: MPD (Music Player Daemon)
- Platform: Raspberry Pi Foundation

## License

This project inherits the license from the original repository.

## Support

For issues and questions:
1. Check the Troubleshooting section
2. Review logs: `sudo journalctl -u encoder-controller -f`
3. Verify I2C devices: `i2cdetect -y 1`
4. Check GitHub repository issues
