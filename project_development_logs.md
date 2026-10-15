# Project Development Logs: AI Instrumento (Grand Piano MIDI Player)

## Project Overview
AI Instrumento is an intelligent, high-fidelity MIDI-to-Grand Piano playback and visualization system. The system detects any `.mid` or `.midi` files in the project directory (including `jan gan man.mid`) and plays their notes on an authentic Grand Piano using both hardware/OS General MIDI synthesis and a real-time web visualizer with falling waterfall notes and an interactive 88-key piano keyboard.

---

### [2026-10-15] - Initial Project Setup & Environment Security
- Initialized local Git repository.
- Created `.gitignore` to ensure `.env` and sensitive access tokens are strictly excluded from version control and GitHub commits.
- Tested and verified Windows Multimedia API (`winmm.dll`) MIDI output with General MIDI Program 0 (Acoustic Grand Piano).
- Verified `mido` library for parsing and processing MIDI files.

### [2026-10-15] - Core Piano Engine Implementation (piano_engine.py)
- Created `piano_engine.py` featuring:
  - `WindowsMidiSynthesizer`: Low-latency native Windows Multimedia API wrapper (`winmm.dll`) that configures MIDI channels directly to General MIDI Program 0 (Acoustic Grand Piano) with velocity dynamics, volume, pan, and sustain pedal (CC 64) support.
  - `MidiScanner`: Automatically scans directory for all `.mid` and `.midi` files, parses tracks, tempos, and generates structured time-indexed note events.
  - `GrandPianoPlayer`: Multi-threaded real-time MIDI playback engine with play/pause/resume/stop controls, speed adjustment, and live note callback hooks.

### [2026-10-15] - Terminal CLI Interactive Player (play_piano.py)
- Created `play_piano.py` providing:
  - Automatic detection of `.mid` files in the directory.
  - Interactive selection menu or direct filename argument support.
  - Real-time ASCII/Unicode piano keyboard visualization rendered dynamically with `rich` console panels.
  - Non-blocking keyboard hotkeys for Windows (`msvcrt`): Spacebar (Play/Pause), `+`/`-` (Tempo/Speed change), `R` (Restart), `Q` (Stop & Quit).
  - Live progress bar, time indicators, active note name list, and frequency mapping.

### [2026-10-15] - Web Visual Studio UI (web/index.html & web/style.css)
- Designed and created `web/index.html` offering:
  - Concert Grand Piano aesthetic with Steinway & Sons style fallboard.
  - HTML5 canvas waterfall visualizer (Synthesia style) for incoming falling notes.
  - Full 88-key grand piano keyboard interface.
  - Active MIDI file selector, directory refresh button, and drag-and-drop file import badge.
  - Playback control center: Play/Pause/Stop, Scrub bar, Tempo chip presets and custom slider, Volume control, Grand Piano track filter toggle, and key labels toggle.
- Created `web/style.css` featuring:
  - Luxury Steinway ebony and gold styling, responsive layout, dark concert hall gradients.
  - Detailed 88-key keyboard geometry with ivory-white and obsidian-black keys, realistic press offsets, and vibrant golden illumination glow on active notes.
  - Glowing timeline scrub bar and modern playback control center.

### [2026-10-15] - Web Audio Synthesizer & Canvas Visualizer (web/piano.js)
- Implemented `web/piano.js` containing:
  - `GrandPianoAudio`: Physical acoustic grand piano modeling with Web Audio API (multi-partial harmonic series, inharmonicity coefficient for steel strings, percussive hammer strike transient impulse, register-dependent decay, and dynamics compressor).
  - `PianoKeyboard`: Interactive 88-key layout (MIDI 21 A0 to 108 C8) with mouse click trigger, keyboard keypress animation, and coordinate positioning.
  - `WaterfallVisualizer`: 60fps HTML5 canvas Synthesia waterfall animation aligning falling note bars precisely with the piano keys.
  - `GrandPianoStudio`: Central orchestrator integrating real-time playback, scrubbing, speed controls, note scheduling, and dual sound engine switching (Web Audio vs Native Windows MIDI).

### [2026-10-15] - Unified Web Server & API Backend (app.py)
- Created `app.py` built on standard library HTTP server (with 0 external web framework overhead):
  - Serves static front-end assets from `./web`.
  - Exposes `/api/files` to dynamically scan and deliver all `.mid` files with duration, track list, and note counts.
  - Exposes `/api/parse/<filename>` delivering pre-calculated note coordinate events for instant client waterfall rendering.
  - Exposes `/api/play-native`, `/api/pause-native`, `/api/stop-native` to allow driving native Windows General MIDI Grand Piano audio directly from the web interface.
  - Exposes `/api/upload` supporting drag-and-drop file ingestion directly into the working directory.
  - Includes automated browser opening and clean port fallback.

### [2026-10-15] - Automated Directory Watch & Play Daemon (watch_and_play.py)
- Created `watch_and_play.py` providing:
  - Continuous directory polling for any existing and newly dropped `.mid` or `.midi` files.
  - Automatic invocation of Grand Piano playback engine whenever a new file is detected.
  - Graceful interrupt handling and clean soundcard channel release on exit.

### [2026-10-15] - Dependency Specification (requirements.txt)
- Created `requirements.txt` documenting essential packages: `mido` (MIDI parsing) and `rich` (terminal visualizer).

### [2026-10-15] - Documentation & User Guide (README.md)
- Created comprehensive `README.md` documenting:
  - Architecture overview and sound synthesis specifications.
  - Quick-start guide for launching the Web Studio (`python app.py`).
  - Terminal CLI player execution instructions (`python play_piano.py`) with interactive key bindings.
  - Auto-watch daemon usage (`python watch_and_play.py`).
  - File structure and OS compatibility matrix.

### [2026-10-15] - Testing, Windows UTF-8 Terminal Fixes & Verification
- Resolved Windows CP1252 charmap encoding limitations by ensuring proper `sys.stdout.reconfigure(encoding="utf-8")` and ASCII-safe fallback console badges across all CLI scripts (`app.py`, `play_piano.py`, `watch_and_play.py`).
- Conducted automated integration testing of server REST endpoints:
  - Verified `/api/files` accurately discovers `jan gan man.mid` and extracts song metadata.
  - Verified `/api/parse/jan gan man.mid` successfully parsed 2,159 note events with millisecond precision.
- Verified Windows Multimedia API (`winmm.dll`) real-time note playback on General MIDI Acoustic Grand Piano (Program 0).










