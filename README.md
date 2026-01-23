# Radio Project Setup Guide

This guide walks you through setting up the internet radio on a Raspberry Pi with HiFiBerry.

## Supported Hardware

- **Raspberry Pi**: Pi Zero 2 W (or any Pi with 40-pin GPIO)
- **HiFiBerry Models**: 
  - AMP4
  - MiniAmp
- **Controls**:
  - Adafruit I2C Rotary Encoder (volume control & play/pause)
  - Two 10-position BCD rotary switches (bank and station selection)
  - Optional: ON/OFF switch for shuffle mode

## Quick Setup

### 1. Install Raspberry Pi OS Lite

Use Raspberry Pi Imager to install Raspberry Pi OS Lite (64-bit) on your microSD card.
- Configure WiFi and enable SSH during setup
- Set hostname (e.g., `r1`)
- Create user `radio`

### 2. Initial Boot Configuration

SSH into your Pi and update:

```bash
sudo apt update
sudo apt upgrade -y
```

### 3. Clone the Repository

```bash
cd /home/radio
git clone https://github.com/jodazsa/radio.git
cd radio
```

### 4. Configure Hardware

Copy and customize the hardware config:

```bash
cp config/hardware-config.yaml /home/radio/hardware-config.yaml
nano /home/radio/hardware-config.yaml
```

Edit the file to match your setup:
- Set `hifiberry_model` to `"amp4"` or `"miniamp"`
- Set `auto_update.github_url` to your stations.yaml GitHub URL
  - Use the "raw" GitHub URL (click "Raw" button when viewing file on GitHub)
  - Example: `https://raw.githubusercontent.com/username/repo/main/config/stations.yaml`
  - Each Pi can pull from a different URL for different station lists!
- Set `auto_update.enabled` to `false` if you want to disable auto-updates
- Set `paths.stations_yaml` if using a custom local path
- Set `paths.audio_base` if storing audio files elsewhere
- Adjust GPIO pins if needed
- Configure volume settings

### 5. Run Hardware Setup

```bash
chmod +x setup-hardware.sh
./setup-hardware.sh
```

This will:
- Configure boot settings for your HiFiBerry model
- Show you the MPD audio configuration
- Display GPIO pin assignments

### 6. Configure MPD

Edit MPD configuration:

```bash
sudo nano /etc/mpd.conf
```

Find the `audio_output` section and replace it with the configuration shown by the setup script.

### 7. Enable I2C

```bash
sudo raspi-config
```

Navigate to: Interface Options → I2C → Enable

Reboot:

```bash
sudo reboot
```

### 8. Install Dependencies

After reboot:

```bash
sudo apt install -y mpd mpc i2c-tools python3-pip python3-yaml
pip3 install --break-system-packages adafruit-circuitpython-seesaw RPi.GPIO
```

Note: We use MPD for all playback (streams and MP3 files), so MPV and ffmpeg are not needed.

### 9. Install Radio Scripts

```bash
cd /home/radio/radio
chmod +x install.sh
./install.sh
```

### 10. Add Audio Files (Optional)

For banks 8 (GTA) and 9 (Recorded Shows), copy your audio files:

```bash
mkdir -p /home/radio/audio/GTA
mkdir -p /home/radio/audio/recordedshows
```

Use `scp` or WinSCP to transfer files from your computer.

### 11. Test

Play a station:

```bash
radio-play 0 0
```

Check status:

```bash
radio-status
```

Watch station changes:

```bash
tail -f /home/radio/station.log
```

## Hardware Wiring

### Rotary Encoder (I2C)
- VCC → 3.3V
- GND → Ground
- SDA → GPIO 2 (SDA)
- SCL → GPIO 3 (SCL)

### Station Selector Switch (BCD)
See `hardware-config.yaml` for GPIO assignments (default: 17, 7, 22, 23)

### Bank Selector Switch (BCD)
See `hardware-config.yaml` for GPIO assignments (default: 5, 6, 13, 8)

### Shuffle Mode Switch (Optional)
- ON/OFF switch connected to GPIO (default: 24)
- When ON: Automatically changes stations every 45 seconds
- When OFF: Normal manual station selection

**Important**: Avoid GPIOs 18, 19, 20, 21 (used by HiFiBerry for I2S audio) and GPIOs 26, 27 (reserved).

## Updating

To update the radio software after making changes on GitHub:

```bash
cd /home/radio/radio
git pull
./install.sh
```

## Commands

- `radio-play <bank> <station>` - Play a specific station
- `radio-status` - Show currently playing station
- `tail -f /home/radio/station.log` - Watch station changes in real-time

## Services

The following services run automatically:
- `mpd` - Music Player Daemon (for streams)
- `volume-control` - Rotary encoder control
- `station-selector` - BCD switch monitoring

Check service status:

```bash
sudo systemctl status volume-control
sudo systemctl status station-selector
```

## Troubleshooting

### No audio
1. Check ALSA mixer: `alsamixer`
   - Digital volume should be 50%+
   - Analogue should be 100%
   - Auto Mute should be ON
2. Test hardware: `speaker-test -c2 -t wav -D hw:1,0`
3. Verify HiFiBerry is detected: `aplay -l`

### Services not starting
Check logs:
```bash
sudo journalctl -u volume-control -n 50
sudo journalctl -u station-selector -n 50
```

### GPIO conflicts
Make sure you're not using GPIOs 18, 19, 20, 21 (reserved for HiFiBerry I2S).

## Setting Up Multiple Pis

1. Clone the repository on each Pi
2. Copy and customize `hardware-config.yaml` for each device
3. Run `setup-hardware.sh` on each Pi
4. Run `install.sh` to install scripts

### Different Stations Per Pi

Each Pi can pull from a different stations list:

**Pi 1 (Living Room) - Rock stations:**
```yaml
auto_update:
  github_url: "https://raw.githubusercontent.com/username/repo/main/stations-rock.yaml"
```

**Pi 2 (Bedroom) - Jazz stations:**
```yaml
auto_update:
  github_url: "https://raw.githubusercontent.com/username/repo/main/stations-jazz.yaml"
```

**Pi 3 (Kitchen) - All stations:**
```yaml
auto_update:
  github_url: "https://raw.githubusercontent.com/username/repo/main/stations-all.yaml"
```

All Pis will automatically stay in sync with their respective GitHub URLs!

### Same Stations, Different Hardware

Multiple Pis with different HiFiBerry models can share the same stations:

**Pi 1 (AMP4):**
```yaml
hifiberry_model: "amp4"
auto_update:
  github_url: "https://raw.githubusercontent.com/username/repo/main/config/stations.yaml"
```

**Pi 2 (MiniAmp):**
```yaml
hifiberry_model: "miniamp"
auto_update:
  github_url: "https://raw.githubusercontent.com/username/repo/main/config/stations.yaml"
```

Same code, same stations, different hardware - just change one line!

The config file makes it easy to adapt to different HiFiBerry models and GPIO layouts!
