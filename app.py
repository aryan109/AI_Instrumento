"""
AI Instrumento - Web Server & Application Backend
Serves the Grand Piano Studio Web UI, exposes REST APIs for MIDI file discovery,
parsing, and native Windows MIDI playback.
"""

import os
import sys
import json
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
import webbrowser
from pathlib import Path
from piano_engine import (
    WindowsMidiSynthesizer,
    GrandPianoPlayer,
    MidiScanner
)

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PORT = 8080
ROOT_DIR = Path(__file__).resolve().parent
WEB_DIR = ROOT_DIR / "web"

# Shared native piano player instance
native_synth = WindowsMidiSynthesizer()
native_player = GrandPianoPlayer(native_synth)


class PianoStudioHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # API: List all MIDI files in directory
        if path == "/api/files":
            files = MidiScanner.list_midi_files(str(ROOT_DIR))
            enriched = []
            for f in files:
                try:
                    summary = MidiScanner.parse_file(f["path"])
                    f["duration"] = summary["duration"]
                    f["total_notes"] = summary["total_notes"]
                    f["lead_notes_count"] = summary["lead_notes_count"]
                    f["lead_track_ids"] = summary["lead_track_ids"]
                    f["tracks"] = summary["tracks"]
                except Exception:
                    f["duration"] = 0
                    f["total_notes"] = 0
                    f["lead_notes_count"] = 0
                    f["lead_track_ids"] = []
                    f["tracks"] = []
                enriched.append(f)

            self.send_json({"files": enriched})
            return

        # API: Parse specific MIDI file
        elif path.startswith("/api/parse/"):
            file_name = urllib.parse.unquote(path[len("/api/parse/"):])
            file_path = ROOT_DIR / file_name
            if not file_path.exists():
                self.send_error(404, f"MIDI file '{file_name}' not found.")
                return

            try:
                data = MidiScanner.parse_file(str(file_path))
                self.send_json(data)
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)
            return

        # Serve static files from web/
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len) if content_len > 0 else b""

        # API: Play via native Windows MIDI synth
        if path == "/api/play-native":
            try:
                payload = json.loads(body.decode('utf-8'))
                file_name = payload.get("file")
                speed = float(payload.get("speed", 1.0))
                solo_lead = bool(payload.get("solo_lead", True))
                selected_track_ids = payload.get("selected_track_ids", None)
                file_path = ROOT_DIR / file_name
                if file_path.exists():
                    native_player.play(
                        str(file_path),
                        speed=speed,
                        solo_lead=solo_lead,
                        selected_track_ids=selected_track_ids,
                        force_grand_piano=True
                    )
                    self.send_json({"status": "playing", "file": file_name, "solo_lead": solo_lead})
                else:
                    self.send_json({"error": "File not found"}, status=404)
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)
            return

        elif path == "/api/export-lead":
            try:
                payload = json.loads(body.decode('utf-8'))
                file_name = payload.get("file")
                file_path = ROOT_DIR / file_name
                if file_path.exists():
                    lead_path = MidiScanner.export_piano_lead_midi(str(file_path))
                    self.send_json({
                        "success": True,
                        "lead_file": os.path.basename(lead_path),
                        "path": lead_path
                    })
                else:
                    self.send_json({"error": "File not found"}, status=404)
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)
            return

        elif path == "/api/pause-native":
            native_player.toggle_pause()
            self.send_json({"status": "paused" if native_player.is_paused else "resumed"})
            return

        elif path == "/api/stop-native":
            native_player.stop()
            self.send_json({"status": "stopped"})
            return


        # API: Upload a new MIDI file
        elif path == "/api/upload":
            try:
                # Basic multipart or direct binary handling
                content_type = self.headers.get('Content-Type', '')
                if 'multipart/form-data' in content_type:
                    boundary = content_type.split("boundary=")[1].encode()
                    parts = body.split(boundary)
                    saved_filename = None
                    for part in parts:
                        if b'filename="' in part:
                            header_part, file_data = part.split(b"\r\n\r\n", 1)
                            # Extract filename
                            header_str = header_part.decode('latin-1')
                            for line in header_str.split("\r\n"):
                                if "filename=" in line:
                                    fname = line.split('filename="')[1].split('"')[0]
                                    fname = os.path.basename(fname)
                                    target = ROOT_DIR / fname
                                    # Strip trailing boundary dashes
                                    clean_data = file_data.rstrip(b"\r\n--")
                                    with open(target, "wb") as f_out:
                                        f_out.write(clean_data)
                                    saved_filename = fname
                                    break
                    if saved_filename:
                        self.send_json({"success": True, "fileName": saved_filename})
                        return

                self.send_json({"error": "Failed to parse uploaded file"}, status=400)
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)
            return

        self.send_error(404, "Unknown API endpoint")

    def send_json(self, data, status=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Clean logging
        pass


def run_server(port=PORT, auto_open=True):
    # Try preferred port, increment if occupied
    server = None
    active_port = port
    for p in range(port, port + 20):
        try:
            server = HTTPServer(("127.0.0.1", p), PianoStudioHandler)
            active_port = p
            break
        except OSError:
            continue

    if not server:
        print("[!] Could not bind to an available port.")
        sys.exit(1)

    url = f"http://localhost:{active_port}"
    print("=" * 60)
    print("      [PIANO] AI INSTRUMENTO - GRAND PIANO STUDIO RUNNING      ")
    print("=" * 60)
    print(f" Web Interface:  {url}")
    print(f" Directory:      {ROOT_DIR}")
    print(f" Native Synth:   Windows General MIDI Acoustic Grand Piano")
    print("=" * 60)
    print(" Press Ctrl+C in terminal to stop server.")
    print("=" * 60)

    if auto_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
    finally:
        native_player.stop()
        native_synth.close()
        server.server_close()


if __name__ == "__main__":
    auto_open = "--no-browser" not in sys.argv
    run_server(auto_open=auto_open)
