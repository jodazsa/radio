#!/usr/bin/env python3
"""Web UI for the Raspberry Pi radio.

Runs alongside radio.py — both talk to MPD via mpc.
No external dependencies beyond Python's standard library + PyYAML.

Configuration via environment variables:
    RADIO_WEB_HOST  — Bind address (default 0.0.0.0)
    RADIO_WEB_PORT  — HTTP port (default 8080)
"""

import json
import logging
import os
import subprocess
import sys
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

STATIONS_PATH = Path("/home/radio/stations.yaml")
STATE_PATH = Path("/home/radio/state.json")
RADIO_HTML_PATH = Path(os.environ.get("RADIO_WEB_UI_PATH", Path(__file__).with_name("radio.html")))
HOST = os.environ.get("RADIO_WEB_HOST", "0.0.0.0")
PORT = int(os.environ.get("RADIO_WEB_PORT", "8080"))

LAST_SELECTION = {
    "bank": 0,
    "station": 0,
    "bank_name": "",
    "station_name": "",
}
_last_selection_time = 0.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("radio-web")


# ── Helpers ───────────────────────────────────────────────

def mpc(*args):
    """Run mpc and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["mpc", *args],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return 127, "", "mpc not installed"
    except Exception as exc:
        log.warning("mpc %s failed: %s", " ".join(args), exc)
        return 1, "", str(exc)


def load_stations():
    """Load stations.yaml."""
    if not STATIONS_PATH.exists():
        raise FileNotFoundError(f"Stations file not found: {STATIONS_PATH}")
    with open(STATIONS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_status():
    """Get current MPD status as a dict."""
    _, raw, _ = mpc("status")
    _, current, _ = mpc("current")

    status = {
        "current": current,
        "state": "stopped",
        "volume": 50,
    }

    for line in raw.splitlines():
        if line.startswith("[playing]"):
            status["state"] = "playing"
        elif line.startswith("[paused]"):
            status["state"] = "paused"
        if "volume:" in line:
            for part in line.split():
                if part.endswith("%") and part[:-1].isdigit():
                    status["volume"] = int(part.rstrip("%"))
                    break

    return status


def stations_json():
    """Return stations as a JSON-friendly list of banks."""
    data = load_stations()
    banks = data.get("banks", {})
    result = []
    for bank_id in sorted(banks.keys()):
        bank = banks[bank_id]
        if not isinstance(bank, dict):
            continue
        bank_entry = {
            "id": bank_id,
            "name": bank.get("name", f"Bank {bank_id}"),
            "stations": [],
        }
        for st_id in sorted(bank.get("stations", {}).keys()):
            st = bank["stations"][st_id]
            if not isinstance(st, dict):
                continue
            bank_entry["stations"].append({
                "id": st_id,
                "name": st.get("name", f"Station {st_id}"),
                "type": st.get("type", ""),
            })
        result.append(bank_entry)
    return result


def play_station(bank_id, station_id):
    """Play a station by bank/station ID. Returns (ok, message)."""
    global _last_selection_time
    data = load_stations()
    banks = data.get("banks", {})
    bank = banks.get(bank_id)
    if not isinstance(bank, dict):
        return False, "Bank not found"
    station = bank.get("stations", {}).get(station_id)
    if not isinstance(station, dict):
        return False, "Station not found"

    name = station.get("name", "Unknown")
    stype = (station.get("type") or "").strip().lower()

    LAST_SELECTION["bank"] = bank_id
    LAST_SELECTION["station"] = station_id
    LAST_SELECTION["bank_name"] = bank.get("name", f"{bank_id}")
    LAST_SELECTION["station_name"] = name
    _last_selection_time = time.time()

    if stype == "stream":
        url = (station.get("url") or "").strip()
        if not url:
            return False, "Station has no stream URL"
        mpc("clear")
        mpc("add", url)
        code, _, err = mpc("play")
        return code == 0, name if code == 0 else err

    if stype == "file":
        path = (station.get("path") or station.get("file") or "").strip()
        if not path:
            return False, "Station has no path"
        mpc("clear")
        mpc("repeat", "on")
        mpc("single", "off")
        mpc("random", "off")
        mpc("add", path)
        code, _, err = mpc("play")
        return code == 0, name if code == 0 else err

    if stype == "dir":
        path = (station.get("path") or station.get("dir") or station.get("directory") or "").strip()
        if not path:
            return False, "Station has no path"
        mpc("clear")
        mpc("repeat", "off")
        mpc("single", "off")
        mpc("random", "off")
        mpc("add", path)
        code, _, err = mpc("play")
        return code == 0, name if code == 0 else err

    # Legacy types from older stations.yaml configs
    if stype in ("mp3_loop_random_start", "file_loop_random_start", "file_loop"):
        path = (station.get("path") or station.get("file") or "").strip()
        if not path:
            return False, "Station has no path"
        mpc("clear")
        mpc("repeat", "on")
        mpc("add", path)
        code, _, err = mpc("play")
        return code == 0, name if code == 0 else err

    if stype in ("mp3_dir_random_start_then_in_order", "dir_random_start_then_in_order", "directory"):
        path = (station.get("path") or station.get("directory") or station.get("dir") or "").strip()
        if not path:
            return False, "Station has no path"
        mpc("clear")
        mpc("add", path)
        code, _, err = mpc("play")
        return code == 0, name if code == 0 else err

    return False, f"Unsupported station type: {stype}"


# ── HTML ──────────────────────────────────────────────────

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Radio</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#1a1a2e;--surface:#16213e;--accent:#e94560;--text:#eee;
  --muted:#8899aa;--border:#0f3460;--hover:#e94560cc;
}
body{
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  background:var(--bg);color:var(--text);min-height:100vh;
  display:flex;flex-direction:column;
}

/* ── Header / Now Playing ── */
header{
  background:var(--surface);padding:1.2rem 1rem;text-align:center;
  border-bottom:2px solid var(--border);position:sticky;top:0;z-index:10;
}
#now-playing{font-size:1.1rem;min-height:1.4em;margin-bottom:.8rem}
#state-badge{
  display:inline-block;font-size:.7rem;text-transform:uppercase;
  letter-spacing:.08em;padding:.15em .5em;border-radius:3px;
  margin-right:.4em;vertical-align:middle;
}
#state-badge.playing{background:#27ae60}
#state-badge.paused{background:#e67e22}
#state-badge.stopped{background:#7f8c8d}

/* ── Controls bar ── */
.controls{
  display:flex;align-items:center;justify-content:center;gap:.8rem;
  flex-wrap:wrap;
}
.controls button{
  background:var(--accent);color:#fff;border:none;border-radius:6px;
  padding:.5rem 1.2rem;font-size:.95rem;cursor:pointer;
  transition:background .15s;
}
.controls button:hover{background:var(--hover)}
.controls button:active{transform:scale(.96)}

.vol-group{display:flex;align-items:center;gap:.4rem}
.vol-group label{font-size:.85rem;color:var(--muted)}
#vol-slider{width:120px;accent-color:var(--accent)}
#vol-value{font-size:.85rem;min-width:2.2em;text-align:right}

/* ── Banks / Stations ── */
main{flex:1;padding:1rem;max-width:600px;margin:0 auto;width:100%}
.bank{margin-bottom:1.2rem}
.bank-name{
  font-size:.8rem;text-transform:uppercase;letter-spacing:.1em;
  color:var(--muted);padding:.3rem 0;border-bottom:1px solid var(--border);
  margin-bottom:.4rem;
}
.station-list{display:flex;flex-direction:column;gap:3px}
.station-btn{
  background:var(--surface);color:var(--text);border:1px solid var(--border);
  border-radius:5px;padding:.55rem .8rem;font-size:.9rem;text-align:left;
  cursor:pointer;transition:background .15s,border-color .15s;
  display:flex;justify-content:space-between;align-items:center;
}
.station-btn:hover{border-color:var(--accent);background:#1a2744}
.station-btn:active{transform:scale(.99)}
.station-btn.active{border-color:var(--accent);background:#2a1530}
.station-type{font-size:.7rem;color:var(--muted);text-transform:uppercase}
</style>
</head>
<body>

<header>
  <div id="now-playing">
    <span id="state-badge" class="stopped">--</span>
    <span id="current-track">Loading...</span>
  </div>
  <div class="controls">
    <button id="btn-prev" title="Previous">&#9664;&#9664;</button>
    <button id="btn-toggle" title="Play / Pause">&#9654; / &#9646;&#9646;</button>
    <button id="btn-next" title="Next">&#9654;&#9654;</button>
    <button id="btn-stop" title="Stop">&#9632;</button>
    <div class="vol-group">
      <label for="vol-slider">Vol</label>
      <input type="range" id="vol-slider" min="0" max="100" value="50">
      <span id="vol-value">50</span>
    </div>
  </div>
</header>

<main id="station-list"></main>

<script>
(function(){
  const $ = s => document.querySelector(s);
  let volTimer = null;

  function api(method, path, body){
    const opts = {method, headers:{"Content-Type":"application/json"}};
    if(body) opts.body = JSON.stringify(body);
    return fetch(path, opts).then(r => r.json()).catch(() => ({}));
  }

  function refreshStatus(){
    api("GET","/api/status").then(d => {
      if(!d.state) return;
      const badge = $("#state-badge");
      badge.textContent = d.state;
      badge.className = d.state;
      $("#current-track").textContent = d.current || "(nothing)";
      $("#vol-slider").value = d.volume;
      $("#vol-value").textContent = d.volume;
    });
  }

  function loadStations(){
    api("GET","/api/stations").then(banks => {
      if(!Array.isArray(banks)) return;
      const container = $("#station-list");
      container.innerHTML = "";
      banks.forEach(bank => {
        const section = document.createElement("div");
        section.className = "bank";
        section.innerHTML = '<div class="bank-name">'+esc(bank.name)+'</div>';
        const list = document.createElement("div");
        list.className = "station-list";
        bank.stations.forEach(st => {
          const btn = document.createElement("button");
          btn.className = "station-btn";
          btn.dataset.bank = bank.id;
          btn.dataset.station = st.id;
          btn.innerHTML = '<span>'+esc(st.name)+'</span><span class="station-type">'+esc(st.type)+'</span>';
          btn.addEventListener("click", () => playStation(bank.id, st.id, btn));
          list.appendChild(btn);
        });
        section.appendChild(list);
        container.appendChild(section);
      });
    });
  }

  function esc(s){ const d=document.createElement("div");d.textContent=s||"";return d.innerHTML; }

  function playStation(bankId, stationId, btn){
    document.querySelectorAll(".station-btn.active").forEach(b => b.classList.remove("active"));
    if(btn) btn.classList.add("active");
    api("POST","/api/play",{bank:bankId, station:stationId}).then(() => {
      setTimeout(refreshStatus, 500);
    });
  }

  $("#btn-toggle").addEventListener("click", () => {
    api("POST","/api/toggle").then(() => setTimeout(refreshStatus, 300));
  });
  $("#btn-stop").addEventListener("click", () => {
    api("POST","/api/stop").then(() => setTimeout(refreshStatus, 300));
  });
  $("#btn-prev").addEventListener("click", () => {
    api("POST","/api/prev").then(() => setTimeout(refreshStatus, 500));
  });
  $("#btn-next").addEventListener("click", () => {
    api("POST","/api/next").then(() => setTimeout(refreshStatus, 500));
  });

  $("#vol-slider").addEventListener("input", e => {
    $("#vol-value").textContent = e.target.value;
    clearTimeout(volTimer);
    volTimer = setTimeout(() => {
      api("POST","/api/volume",{volume: parseInt(e.target.value)});
    }, 150);
  });

  loadStations();
  refreshStatus();
  setInterval(refreshStatus, 3000);
})();
</script>
</body>
</html>"""


# ── HTTP Handler ──────────────────────────────────────────

class RadioHandler(BaseHTTPRequestHandler):
    """Handle HTTP requests for the radio web UI."""

    def log_message(self, fmt, *args):
        log.info(fmt, *args)

    def _json(self, data, status=HTTPStatus.OK):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, content, status=HTTPStatus.OK):
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_radio_html(self):
        if not RADIO_HTML_PATH.exists():
            raise FileNotFoundError(f"UI file not found: {RADIO_HTML_PATH} (set RADIO_WEB_UI_PATH or deploy radio.html)")
        return RADIO_HTML_PATH.read_text(encoding="utf-8")

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    # ── GET routes ──

    def do_GET(self):
        if self.path in {"/", "/index.html", "/radio.html"}:
            try:
                self._html(self._read_radio_html())
            except FileNotFoundError as exc:
                self._json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
        elif self.path == "/api/status":
            self._json(get_status())
        elif self.path == "/api/stations":
            try:
                self._json(stations_json())
            except FileNotFoundError as exc:
                self._json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
        elif self.path == "/stations/source":
            self._json({"success": True, "github_url": "", "auto_update_enabled": False})
        elif self.path == "/admin/version":
            self._json({"success": True, "version": "local"})
        elif self.path in {"/admin/log", "/admin/service-logs"}:
            self._json({"success": False, "error": "Not supported in this web server"}, HTTPStatus.NOT_IMPLEMENTED)
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    # ── POST routes ──

    def do_POST(self):
        if self.path == "/api/play":
            body = self._read_body()
            if body is None:
                self._json({"error": "invalid JSON"}, HTTPStatus.BAD_REQUEST)
                return
            raw_bank = body.get("bank")
            raw_station = body.get("station")
            if raw_bank is None or raw_station is None:
                self._json({"error": "bank and station required"}, HTTPStatus.BAD_REQUEST)
                return
            try:
                bank_id = int(raw_bank)
                station_id = int(raw_station)
            except (ValueError, TypeError):
                self._json({"error": "bank and station must be numbers"}, HTTPStatus.BAD_REQUEST)
                return
            try:
                ok, msg = play_station(bank_id, station_id)
            except FileNotFoundError as exc:
                self._json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            if ok:
                self._json({"ok": True, "name": msg})
            else:
                self._json({"error": msg}, HTTPStatus.NOT_FOUND)

        elif self.path == "/api/toggle":
            mpc("toggle")
            self._json({"ok": True})

        elif self.path == "/api/stop":
            mpc("stop")
            self._json({"ok": True})

        elif self.path == "/api/prev":
            mpc("prev")
            self._json({"ok": True})

        elif self.path == "/api/next":
            mpc("next")
            self._json({"ok": True})

        elif self.path == "/api/volume":
            body = self._read_body()
            if body is None:
                self._json({"error": "invalid JSON"}, HTTPStatus.BAD_REQUEST)
                return
            raw_vol = body.get("volume")
            if raw_vol is None:
                self._json({"error": "volume required"}, HTTPStatus.BAD_REQUEST)
                return
            try:
                vol = max(0, min(100, int(raw_vol)))
            except (ValueError, TypeError):
                self._json({"error": "volume must be a number"}, HTTPStatus.BAD_REQUEST)
                return
            mpc("volume", str(vol))
            self._json({"ok": True, "volume": vol})

        elif self.path == "/status":
            status = get_status()
            self._json({
                "success": True,
                "volume": status.get("volume", 50),
                "current_track": status.get("current", ""),
                "is_playing": status.get("state") == "playing",
                "is_paused": status.get("state") == "paused",
            })

        elif self.path == "/state":
            result = {
                "success": True,
                "bank": LAST_SELECTION["bank"],
                "station": LAST_SELECTION["station"],
                "bank_name": LAST_SELECTION["bank_name"],
                "station_name": LAST_SELECTION["station_name"],
            }
            # Prefer hardware state (written by radio.py) when it's newer
            try:
                hw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
                if hw.get("timestamp", 0) >= _last_selection_time:
                    b = hw.get("bank", -1)
                    s = hw.get("station", -1)
                    if b >= 0 and s >= 0:
                        result["bank"] = b
                        result["station"] = s
                        result["bank_name"] = ""
                        result["station_name"] = ""
                        try:
                            cfg = load_stations()
                            bank = cfg.get("banks", {}).get(b)
                            if isinstance(bank, dict):
                                result["bank_name"] = bank.get("name", "")
                                st = bank.get("stations", {}).get(s)
                                if isinstance(st, dict):
                                    result["station_name"] = st.get("name", "")
                        except Exception:
                            pass
            except Exception:
                pass
            self._json(result)

        elif self.path == "/stations":
            try:
                banks = []
                for bank in stations_json():
                    banks.append({
                        "bank": bank["id"],
                        "name": bank["name"],
                        "stations": [
                            {"station": st["id"], "name": st["name"]}
                            for st in bank.get("stations", [])
                        ],
                    })
                self._json({"success": True, "banks": banks})
            except FileNotFoundError as exc:
                self._json({"success": False, "error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

        elif self.path == "/command":
            body = self._read_body()
            if body is None:
                self._json({"success": False, "error": "invalid JSON"}, HTTPStatus.BAD_REQUEST)
                return
            command = (body.get("command") or "").strip()

            if command.startswith("radio-play"):
                parts = command.split()
                if len(parts) != 3:
                    self._json({"success": False, "error_type": "command_failed"}, HTTPStatus.BAD_REQUEST)
                    return
                try:
                    bank_id = int(parts[1])
                    station_id = int(parts[2])
                except ValueError:
                    self._json({"success": False, "error_type": "command_failed"}, HTTPStatus.BAD_REQUEST)
                    return
                try:
                    ok, msg = play_station(bank_id, station_id)
                except FileNotFoundError as exc:
                    self._json({"success": False, "error": str(exc), "error_type": "command_failed"}, HTTPStatus.INTERNAL_SERVER_ERROR)
                    return
                if ok:
                    self._json({"success": True, "message": msg})
                else:
                    self._json({"success": False, "error": msg, "error_type": "command_failed"}, HTTPStatus.BAD_REQUEST)
                return

            if command == "mpc play":
                code, _, _ = mpc("play")
            elif command == "mpc pause":
                code, _, _ = mpc("pause")
            elif command.startswith("mpc volume "):
                parts = command.split()
                if len(parts) != 3:
                    self._json({"success": False, "error_type": "command_failed"}, HTTPStatus.BAD_REQUEST)
                    return
                try:
                    volume = max(0, min(100, int(parts[2])))
                except ValueError:
                    self._json({"success": False, "error_type": "command_failed"}, HTTPStatus.BAD_REQUEST)
                    return
                code, _, _ = mpc("volume", str(volume))
            elif command == "sudo shutdown -h now":
                self._json({"success": False, "error_type": "forbidden_command"}, HTTPStatus.FORBIDDEN)
                return
            else:
                self._json({"success": False, "error_type": "forbidden_command"}, HTTPStatus.FORBIDDEN)
                return

            self._json({"success": code == 0})

        elif self.path in {
            "/stations/refresh",
            "/stations/source",
            "/stations/auto-update",
            "/admin/update",
            "/admin/restart",
            "/admin/reboot",
        }:
            self._json({"success": False, "error": "Not supported in this web server"}, HTTPStatus.NOT_IMPLEMENTED)

        else:
            self.send_error(HTTPStatus.NOT_FOUND)


# ── Main ──────────────────────────────────────────────────

if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), RadioHandler)
    log.info("Radio web UI listening on http://%s:%d", HOST, PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down")
    server.server_close()
