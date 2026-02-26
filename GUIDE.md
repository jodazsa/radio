# Simplified Pi Radio — Step-by-Step Guide

## What changed (original → simplified)

| Original | Simplified | Why |
|----------|-----------|-----|
| 15+ files, ~5,500 lines | **4 files, ~400 lines** | Less to break, easier to understand |
| Separate `rotary-controller`, `radio-play`, `radio_lib.py` | **Single `radio.py`** | One file does everything |
| 1,076-line web backend + 1,824-line web UI | **Tiny built-in web UI** | Minimal browser control on your local network |
| Auto-update stations from GitHub | **Removed** | Edit `stations.yaml` directly on the Pi |
| WiFi AP fallback + provisioning | **Removed** | Set up WiFi with `raspi-config` or Pi Imager |
| Fuzzy media matching (roman numerals, legacy prefixes) | **Removed** | Just use correct paths |
| 6 station types with aliases | **3 types: `stream`, `file`, `dir`** | Covers all real usage |
| BCD decode maps, stability windows, glitch filters | **Simple debounce only** | Kept minimal; add back if switches misbehave |
| Playback watchdog with exponential backoff | **Simple watchdog** | Restarts dead streams, no complex backoff |
| 5 systemd services + 1 timer | **2 systemd services** | `radio.py` + small `radio_web.py` web control |
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
├── radio.service         ← Main radio controller service
├── radio-web.service     ← Web UI service
└── radio_web.py          ← Browser-based radio control
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
sudo apt update
sudo apt install -y git
git clone https://github.com/jodazsa/radio.git
cd radio
```

Option B — copy files manually:
```bash
# From your computer:
scp -r radio/ pi@radio.local:~/radio/
# Then on the Pi:
cd ~/radio
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
7. Install and start the systemd services

**Reboot when prompted:**
```bash
sudo reboot
```

## Step 4: Verify it works

After reboot, SSH back in and check:

```bash
# Is the service running?
sudo systemctl status radio radio-web

# Can you see the I2C volume encoder?
i2cdetect -y 1    # Should show device at 0x36

# Is MPD running?
mpc status

# Watch the logs live
sudo journalctl -u radio -u radio-web -f
```

Turn the station and bank switches — you should hear audio and see log entries.

## Browser control (same network)

A web interface is included. After install/reboot:

```bash
# Find your Pi IP
hostname -I

# Open from phone/laptop browser on same network
http://<pi-ip>:8080
```

From the page you can:
- Browse stations grouped by bank and play any of them
- Play/pause, stop, previous/next track
- Adjust volume with a slider (0–100)
- See real-time now-playing status

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

## Power loss resilience

This radio is designed to survive unplanned power loss and run unattended for years. The installer configures multiple layers of protection:

### What happens on power loss

1. Power is cut — the Pi shuts down immediately (no graceful shutdown)
2. On power restore, the Pi boots normally
3. systemd starts MPD, then the radio service
4. The radio controller restores volume from the saved state file
5. It reads the physical switch positions and starts the correct station
6. The stream watchdog monitors for playback health

**Recovery is fully automatic — no user intervention required.**

### Protection layers

| Layer | What it does | Protects against |
|-------|-------------|-----------------|
| **State persistence** | Volume saved to `/home/radio/state.json` using atomic writes (write-to-temp, fsync, rename) | Volume reset after power loss |
| **Hardware watchdog** | `bcm2835_wdt` kernel module reboots the Pi if the OS hangs | Kernel panic, total system hang |
| **Service watchdog** | systemd restarts radio.py if it stops sending keepalives (30s timeout) | Process hang, deadlock |
| **Auto-restart** | `Restart=always` in systemd with rate limiting (10 restarts per 5 minutes) | Process crash, unexpected exit |
| **Signal handling** | SIGTERM handler saves state before exit | Clean shutdown on `systemctl stop` |
| **Volatile journal** | System logs stored in RAM, not on SD card | SD card wear from logging |
| **tmpfs mounts** | `/tmp` and `/var/tmp` mounted as RAM disks | SD card wear from temp files |
| **Filesystem tuning** | `noatime,commit=60` mount options on root | SD card wear from frequent writes |
| **Swap disabled** | No swap file on SD card | SD card wear from swapping |
| **Stream watchdog** | Auto-restarts dead internet streams after 15s grace period | Stream server disconnects, network glitches |
| **Config hot-reload** | `stations.yaml` changes detected without restart (checked every 30s) | Need to edit stations without downtime |
| **Filesystem health check** | Daily check for ext4 errors and I/O errors in dmesg | Early warning of SD card failure |
| **Resource limits** | Memory capped at 128M, CPU at 50% | Runaway processes consuming resources |
| **I2C error handling** | Transient I2C read failures fall back to last known value | Electrical noise, bus contention |

### State file format

The state file at `/home/radio/state.json` uses atomic writes to prevent corruption:

```json
{"volume": 72, "bank": 3, "station": 5, "timestamp": 1709000000}
```

- Written at most once every 5 seconds (only when state changes)
- Uses write-to-temp → fsync → rename pattern (safe against power loss mid-write)
- If corrupted on read, it's deleted and defaults are used
- On clean shutdown (SIGTERM), state is saved immediately

### SD card longevity tips

- Use a high-endurance SD card (Samsung PRO Endurance, SanDisk MAX Endurance)
- The install script already minimizes writes (volatile journal, tmpfs, noatime)
- Monitor SD health: `sudo dmesg | grep -i "mmc\|error"`
- Keep a backup SD card with the same setup ready to swap in

---

## Web UI details

The built-in web UI (`radio_web.py`) is a single-page app served on port 8080. It talks to MPD via `mpc` commands, just like `radio.py`. Both coexist safely.

If you prefer a different web client, MPD is running on `localhost:6600` and any MPD client will work (e.g. **ympd**, **Rompr**).
