#!/usr/bin/env python3
"""Simple web UI for controlling the radio over the local network."""

import json
import logging
import os
import subprocess
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml

STATIONS_PATH = Path("/home/radio/stations.yaml")
HOST = os.environ.get("RADIO_WEB_HOST", "0.0.0.0")
PORT = int(os.environ.get("RADIO_WEB_PORT", "8080"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("radio-web")


def mpc(*args):
    """Run mpc and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["mpc", *args],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return 127, "", "mpc not installed"
    except Exception as exc:
        return 1, "", str(exc)


def load_stations():
    if not STATIONS_PATH.exists():
        return {}
    with open(STATIONS_PATH, "r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def get_station(data, bank_id, station_id):
    bank = data.get("banks", {}).get(bank_id)
    if not isinstance(bank, dict):
        return None
    station = bank.get("stations", {}).get(station_id)
    if not isinstance(station, dict):
        return None
    return station


def play_station(bank_id, station_id):
    stations = load_stations()
    station = get_station(stations, bank_id, station_id)
    if not station:
        return False, f"No station for bank {bank_id}, station {station_id}"

    station_type = (station.get("type") or "").strip().lower()
    if station_type == "stream":
        url = (station.get("url") or "").strip()
        if not url:
            return False, "Station has no stream URL"
        mpc("clear")
        mpc("add", url)
        code, _, err = mpc("play")
        return code == 0, err or ""

    if station_type in ("file", "dir"):
        path = (station.get("path") or "").strip()
        if not path:
            return False, "Station has no path"
        mpc("clear")
        mpc("add", path)
        code, _, err = mpc("play")
        return code == 0, err or ""

    return False, f"Unsupported station type: {station_type}"


def parse_status():
    _, status_text, _ = mpc("status")
    _, volume_text, _ = mpc("volume")

    state = "stopped"
    if "[playing]" in status_text:
        state = "playing"
    elif "[paused]" in status_text:
        state = "paused"

    volume = None
    for token in volume_text.split():
        if token.endswith("%") and token[:-1].isdigit():
            volume = int(token[:-1])
            break

    track_line = status_text.splitlines()[0] if status_text else ""
    return {
        "state": state,
        "volume": volume,
        "track": track_line,
    }


def station_options_html(stations):
    options = []
    for bank_id, bank in sorted(stations.get("banks", {}).items()):
        if not isinstance(bank, dict):
            continue
        for station_id, station in sorted(bank.get("stations", {}).items()):
            if not isinstance(station, dict):
                continue
            name = station.get("name") or f"Bank {bank_id} / Station {station_id}"
            options.append(
                f'<option value="{bank_id}:{station_id}">Bank {bank_id} · Station {station_id} — {name}</option>'
            )
    return "\n".join(options) or '<option disabled>No stations configured</option>'


class RadioHandler(BaseHTTPRequestHandler):
    def _json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redirect_home(self):
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", "/")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self._json(parse_status())
            return

        if parsed.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        stations = load_stations()
        status = parse_status()
        message = parse_qs(parsed.query).get("msg", [""])[0]

        body = f"""<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Radio Control</title>
  <style>
    body {{ font-family: sans-serif; max-width: 640px; margin: 2rem auto; padding: 0 1rem; }}
    h1 {{ margin-bottom: 0.5rem; }}
    .card {{ border: 1px solid #ddd; border-radius: 10px; padding: 1rem; margin-bottom: 1rem; }}
    button, select {{ font-size: 1rem; padding: 0.5rem; width: 100%; margin-top: 0.5rem; }}
    .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; }}
    .msg {{ color: #0a5; font-weight: 600; min-height: 1.2rem; }}
    .muted {{ color: #666; font-size: 0.9rem; }}
  </style>
</head>
<body>
  <h1>Radio Control</h1>
  <p class=\"muted\">Open this page from any device on the same network.</p>

  <div class=\"card\">
    <strong>Status:</strong> {status['state']}<br>
    <strong>Volume:</strong> {status['volume'] if status['volume'] is not None else 'unknown'}%<br>
    <strong>Now playing:</strong> {status['track'] or 'Nothing'}
  </div>

  <div class=\"card\">
    <form method=\"post\" action=\"/action/play_station\">
      <label for=\"station\"><strong>Choose station</strong></label>
      <select name=\"station\" id=\"station\">{station_options_html(stations)}</select>
      <button type=\"submit\">Play selected station</button>
    </form>
  </div>

  <div class=\"card\">
    <div class=\"row\">
      <form method=\"post\" action=\"/action/toggle\"><button type=\"submit\">Play / Pause</button></form>
      <form method=\"post\" action=\"/action/stop\"><button type=\"submit\">Stop</button></form>
    </div>
    <div class=\"row\">
      <form method=\"post\" action=\"/action/vol_down\"><button type=\"submit\">Volume -5</button></form>
      <form method=\"post\" action=\"/action/vol_up\"><button type=\"submit\">Volume +5</button></form>
    </div>
  </div>

  <p class=\"msg\">{message}</p>
</body>
</html>
""".encode("utf-8")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        parsed = urlparse(self.path)
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len else ""
        form = parse_qs(body)
        message = "Done"

        if parsed.path == "/action/toggle":
            mpc("toggle")
        elif parsed.path == "/action/stop":
            mpc("stop")
        elif parsed.path == "/action/vol_up":
            mpc("volume", "+5")
        elif parsed.path == "/action/vol_down":
            mpc("volume", "-5")
        elif parsed.path == "/action/play_station":
            selected = form.get("station", [""])[0]
            try:
                bank_raw, station_raw = selected.split(":", 1)
                ok, detail = play_station(int(bank_raw), int(station_raw))
                message = "Playing selected station" if ok else f"Could not play: {detail}"
            except ValueError:
                message = "Invalid station selection"
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", f"/?msg={message.replace(' ', '+')}")
        self.end_headers()


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), RadioHandler)
    log.info("Radio web UI listening on http://%s:%d", HOST, PORT)
    server.serve_forever()
