# Simplified Pi Radio — Step-by-Step Guide

## What changed (original → simplified)

| Original | Simplified | Why |
|----------|-----------|-----|
| 15+ files, ~5,500 lines | **4 files, ~400 lines** | Less to break, easier to understand |
| Separate `rotary-controller`, `radio-play`, `radio_lib.py` | **Single `radio.py`** | One file does everything |
| 1,076-line web backend + 1,824-line web UI | **Removed** | MPD is still there — bolt on a web UI later if needed |
| Auto-update stations from GitHub | **Removed** | Edit `stations.yaml` directly on the Pi |
| WiFi AP fallback + provisioning | **Removed** | Set up WiFi with `raspi-config` or Pi Imager |
| Fuzzy media matching (roman numerals, legacy prefixes) | **Removed** | Just use correct paths |
| 6 station types with aliases | **3 types: `stream`, `file`, `dir`** | Covers all real usage |
| BCD decode maps, stability windows, glitch filters | **Simple debounce only** | Kept minimal; add back if switches misbehave |
| Playback watchdog with exponential backoff | **Simple watchdog** | Restarts dead streams, no complex backoff |
| 5 systemd services + 1 timer | **1 systemd service** | Just runs `radio.py` |
| Full config validation (50+ checks) | **Fail-fast on missing keys** | Python will tell you what's wrong |
| `deploy-rotary.sh` + `install-rotary.sh` | **Single `install.sh`** | One script, run once |

---

## Files in this project

```
radio-simple/
├── GUIDE.md              ← You're reading this
├── install.sh            ← Run once on a fresh Pi
├── radio.py              ← The entire radio controller
├── stations.yaml         ← Your stations (edit this)
└── radio.service         ← Systemd unit file
```

---

## Step 1: Prepare your Raspberry Pi

Use **Raspberry Pi Imager** to flash **Raspberry Pi OS Lite 64-bit (Bookworm)**.

In Imager's advanced settings, configure:
- Hostname (e.g. `radio`)
- Username / password
- WiFi credentials
- Enable SSH

Boot the Pi and SSH in.

## Step 2: Get the files onto the Pi

Option A — clone from a repo (if you push these files to GitHub):
```bash
cd ~
git clone https://github.com/YOUR_USER/radio-simple.git
cd radio-simple
```

Option B — copy files manually:
```bash
# From your computer:
scp -r radio-simple/ radio@radio.local:~/radio-simple/
# Then on the Pi:
cd ~/radio-simple
```

## Step 3: Run the installer

```bash
chmod +x install.sh
./install.sh
```

This will:
1. Update system packages
2. Enable I2C
3. Install MPD, mpc, Python libraries
4. Create the `radio` user and directories
5. Configure MPD and the HiFiBerry DAC
6. Copy `radio.py` and `stations.yaml` into place
7. Install and start the systemd service

**Reboot when prompted:**
```bash
sudo reboot
```

## Step 4: Verify it works

After reboot, SSH back in and check:

```bash
# Is the service running?
sudo systemctl status radio

# Can you see the I2C volume encoder?
i2cdetect -y 1    # Should show device at 0x36

# Is MPD running?
mpc status

# Watch the logs live
sudo journalctl -u radio -f
```

Turn the station and bank switches — you should hear audio and see log entries.

## Step 5: Edit your stations

```bash
sudo nano /home/radio/stations.yaml
```

After editing, restart the service to pick up changes (or just turn a switch — it reloads automatically):

```bash
sudo systemctl restart radio
```

### Station types

**stream** — Internet radio:
```yaml
0:
  name: "WWOZ New Orleans"
  type: stream
  url: "http://wwoz-sc.streamguys.com/wwoz-hi.mp3"
```

**file** — Single local audio file (loops forever):
```yaml
1:
  name: "Rain Sounds"
  type: file
  path: "ambient/rain.mp3"
```
Paths are relative to `/home/radio/audio/`.

**dir** — Play all files in a directory:
```yaml
2:
  name: "Bob Dylan"
  type: dir
  path: "artists/bob-dylan"
```

## Step 6: Add local music (optional)

```bash
# From your computer, copy files to the Pi:
scp -r "my-music/" radio@radio.local:/home/radio/audio/my-music/

# On the Pi, tell MPD to scan for new files:
mpc update
```

---

## Hardware wiring reference

This matches the original project's wiring. No changes needed.

**Station BCD switch** (10-position) → GPIO pins:
- bit0 (value 1): GPIO 9
- bit1 (value 2): GPIO 10
- bit2 (value 4): GPIO 22
- bit3 (value 8): GPIO 17

**Bank BCD switch** (10-position) → GPIO pins:
- bit0 (value 1): GPIO 5
- bit1 (value 2): GPIO 6
- bit2 (value 4): GPIO 13
- bit3 (value 8): GPIO 11

**Volume encoder**: I2C via Adafruit Seesaw at address `0x36`

**Play/pause toggle switch**: GPIO 24

All switch pins use internal pull-ups (active LOW).

---

## Troubleshooting

**No sound:**
```bash
aplay -l                           # Check audio devices
mpc outputs                        # Check MPD outputs
sudo systemctl restart mpd radio   # Restart everything
```

**Switches not responding:**
```bash
# Check GPIO reads directly
python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.setup(9, GPIO.IN, pull_up_down=GPIO.PUD_UP); print(GPIO.input(9))"
```

**Volume encoder not found:**
```bash
i2cdetect -y 1   # Should show 0x36
```

**Service won't start:**
```bash
sudo journalctl -u radio -n 50 --no-pager
```

---

## Adding a web UI later

MPD is running on `localhost:6600`. Any MPD web client will work. Popular options:
- **ympd** — lightweight web MPD client
- **Rompr** — full-featured
- Or build your own that talks to MPD

The radio.py controller and a web UI can coexist — they both just talk to MPD.
