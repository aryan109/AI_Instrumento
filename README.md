# 🎹 AI Instrumento - Grand Piano MIDI System

An intelligent, high-fidelity MIDI-to-Grand Piano playback and visualization system. Whenever a `.mid` or `.midi` file is present in the directory (such as `jan gan man.mid`), the system can play its notes with authentic acoustic grand piano timbre and dynamic visualization.

---

## ✨ Features

- **Acoustic Grand Piano Sound Engines**:
  - **Windows Native Multimedia API (`winmm.dll`)**: Zero-latency direct hardware playback via Windows General MIDI Instrument 0 (Acoustic Grand Piano) with dynamic velocity, volume, pan, and sustain pedal (CC 64) support.
  - **Studio Web Audio Synthesizer**: Physical multi-partial acoustic piano modeling in the browser with inharmonic steel string harmonics, hammer strike percussive noise transient, and register-dependent decay.
- **Synthesia Waterfall Visualizer**: 60 FPS HTML5 canvas displaying cascading notes falling onto the corresponding piano keys.
- **88-Key Concert Grand Piano Keyboard**: Full A0 (MIDI 21) to C8 (MIDI 108) layout with authentic ivory and obsidian key textures, press depth physics, and gold illumination when notes strike.
- **Interactive Terminal Visualizer**: Terminal CLI interface with real-time ASCII/Unicode piano keyboard, dynamic time progress bar, and active note name display.
- **Directory Detection & Auto-Watch Daemon**: Automatically scans and lists all `.mid` files in the directory; can continuously watch for new files dropped into the folder and trigger playback.
- **Full Playback Controls**: Play, Pause, Resume, Stop, Scrub/Seek timeline, Tempo multiplier (0.25x – 2.0x), Volume slider, and Grand Piano track isolation.

---

## 🚀 Quick Start

### 1. Requirements
Ensure the dependencies are installed:
```bash
pip install -r requirements.txt
```

### 2. Launching the Web Visual Studio (Recommended)
To launch the concert hall interface with the 88-key grand piano and waterfall visualizer:
```bash
python app.py
```
This automatically opens `http://localhost:8080` in your web browser.

- Select any `.mid` file from the top dropdown (e.g. `jan gan man.mid`).
- Click **PLAY ON GRAND PIANO**.
- Switch between **Studio Web Audio** and **Windows Native MIDI** at any time.
- Drag and drop any new `.mid` file into the browser window to load and play it immediately.

### 3. Launching the Terminal CLI Player
To play directly in your terminal with live keyboard art and hotkeys:
```bash
# Auto-detects and plays available .mid files
python play_piano.py

# Or specify a specific file:
python play_piano.py "jan gan man.mid"
```
**Terminal Hotkeys**:
- `Space`: Pause / Resume playback
- `+` / `-`: Increase or decrease tempo speed
- `R`: Restart song from the beginning
- `Q`: Stop and exit

### 4. Running the Auto-Watch & Play Daemon
To run a background daemon that monitors the directory and automatically plays any newly added `.mid` files:
```bash
python watch_and_play.py
```

---

## 📂 File Structure

| File | Purpose |
|---|---|
| `piano_engine.py` | Core engine: `WindowsMidiSynthesizer` (winmm.dll), `MidiScanner`, `GrandPianoPlayer` |
| `play_piano.py` | Interactive terminal CLI player with real-time ASCII 88-key piano keyboard |
| `app.py` | Standard HTTP server and REST API for MIDI file discovery and playback |
| `watch_and_play.py` | Directory watcher daemon that triggers Grand Piano playback on file detection |
| `web/index.html` | Luxury Concert Grand visual studio interface with fallboard and controls |
| `web/piano.js` | Web Audio physical grand piano synthesis, 88-key logic, and waterfall canvas |
| `web/style.css` | Steinway & Sons luxury concert piano dark theme styling |
| `jan gan man.mid` | Sample MIDI file (National Anthem of India with Studio Grand piano tracks) |
| `project_development_logs.md` | Comprehensive log of every step, component, and update |

---

## 🛠 Supported Operating Systems
- **Windows**: Full support for both Windows Native General MIDI (`winmm.dll`) and Web Audio visualizer.
- **macOS / Linux**: Full support for the Web Visual Studio and terminal visualizer.
