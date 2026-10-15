# 🎹 AI Instrumento - Smart Grand Piano MIDI System

An intelligent, high-fidelity MIDI-to-Grand Piano playback and visualization system with **Smart Track Identification**. Whenever a `.mid` or `.midi` file is present in the directory (such as `jan gan man.mid`), the system analyzes every track, identifies the instruments, and focuses specifically on extracting and playing the **Main Piano Lead** on an authentic Acoustic Grand Piano.

---

## ✨ Features

- **Smart MIDI Track Identification**:
  - Automatically parses all tracks, channels, program changes, and melodic registers.
  - Categorizes tracks into roles: `PIANO_LEAD`, `PIANO_ACCOMPANIMENT`, `GUITAR`, `BASS`, `DRUMS`, and `OTHER`.
  - Intelligently recognizes segmented piano phrases (e.g. tracks 16–28 in `jan gan man.mid`) and unites them into a cohesive **Main Piano Lead**.
- **Main Piano Lead Focus (Your Main Purpose)**:
  - **Solo Main Piano Lead Mode**: Plays exclusively the piano lead melody on the Grand Piano with zero interference from backing tracks.
  - **Individual Track Solo**: Select any individual track from a dropdown or track inspector to play solo on the Grand Piano.
  - **Lead MIDI Exporter**: Export the extracted Main Piano Lead as an individual standalone `.mid` file (e.g. `jan gan man_piano_lead.mid`) with 1 click.
- **Acoustic Grand Piano Sound Engines**:
  - **Windows Native Multimedia API (`winmm.dll`)**: Zero-latency direct hardware playback via Windows General MIDI Instrument 0 (Acoustic Grand Piano) with dynamic velocity, volume, pan, and sustain pedal (CC 64) support.
  - **Studio Web Audio Synthesizer**: Physical multi-partial acoustic piano modeling in the browser with inharmonic steel string harmonics, hammer strike percussive noise transient, and register-dependent decay.
- **Synthesia Waterfall Visualizer**: 60 FPS HTML5 canvas displaying radiant gold cascading notes falling onto the corresponding piano keys.
- **88-Key Concert Grand Piano Keyboard**: Full A0 (MIDI 21) to C8 (MIDI 108) layout with authentic ivory and obsidian key textures, press depth physics, and gold illumination when notes strike.
- **Interactive Terminal Visualizer**: Terminal CLI interface with real-time ASCII/Unicode piano keyboard, dynamic time progress bar, and active note name display.
- **Directory Detection & Auto-Watch Daemon**: Automatically scans and lists all `.mid` files in the directory; can continuously watch for new files dropped into the folder and trigger playback.

---

## 🚀 Quick Start

### 1. Requirements
Ensure dependencies are installed:
```bash
pip install -r requirements.txt
```

### 2. Launching the Web Visual Studio (Recommended)
To launch the concert hall interface with the 88-key grand piano, smart mode switcher, and waterfall visualizer:
```bash
python app.py
```
This automatically opens `http://localhost:8080` in your web browser.

- **Solo Main Piano Lead**: Click the **★ Solo Main Piano Lead** tab (active by default) and hit **PLAY MAIN PIANO LEAD**.
- **Inspect Tracks**: Click **🔍 Tracks** to view the smart classification table of all tracks, instruments, and notes.
- **Solo Any Track**: Choose **🎛 Solo Individual Track** from the tabs or click "Solo on Piano" in the inspector.
- **Export Piano Lead**: Click **💾 Export Lead .mid** to save the clean individual piano melody file.
- **Switch Sound Engine**: Choose between **Studio Web Audio** or **Windows Native MIDI (winmm)** anytime.

### 3. Launching the Terminal CLI Player
To play directly in your terminal with smart track inspection:
```bash
# Interactive selection menu with track inspection:
python play_piano.py

# Play Solo Main Piano Lead directly:
python play_piano.py --lead

# Play a specific individual track solo (e.g. Track 16):
python play_piano.py --track 16

# Export Main Piano Lead as a standalone .mid file:
python play_piano.py --export-lead
```

**Terminal Hotkeys**:
- `Space`: Pause / Resume playback
- `+` / `-`: Increase or decrease tempo speed
- `R`: Restart song from the beginning
- `Q`: Stop and exit

### 4. Running the Auto-Watch & Play Daemon
To run a background daemon that monitors the directory and automatically plays the Main Piano Lead of any newly added `.mid` files:
```bash
python watch_and_play.py
```

---

## 📂 File Structure

| File | Purpose |
|---|---|
| `piano_engine.py` | Smart engine: `SmartTrackClassifier`, `MidiScanner`, `WindowsMidiSynthesizer`, and `GrandPianoPlayer` |
| `play_piano.py` | Interactive terminal CLI player with smart track inspection, solo lead mode, and ASCII piano |
| `app.py` | Standard HTTP server and REST API for MIDI file discovery, parsing, lead export, and playback |
| `watch_and_play.py` | Directory watcher daemon that triggers Grand Piano playback on file detection |
| `web/index.html` | Luxury Concert Grand studio with Smart Track Switcher, inspector modal, and controls |
| `web/piano.js` | Web Audio physical grand piano synthesis, 88-key logic, track filtering, and waterfall canvas |
| `web/style.css` | Steinway & Sons luxury concert piano dark theme styling and responsive modal layout |
| `jan gan man.mid` | Full arrangement MIDI file (Acoustic Guitars, Drums, and Studio Grand piano lead) |
| `jan gan man_piano_lead.mid` | Standalone individual MIDI file of the extracted Main Piano Lead melody (131 notes) |
| `project_development_logs.md` | Comprehensive log of every step, component, and update |

---

## 🛠 Supported Operating Systems
- **Windows**: Full support for both Windows Native General MIDI (`winmm.dll`) and Web Audio visualizer.
- **macOS / Linux**: Full support for the Web Visual Studio and terminal visualizer.
