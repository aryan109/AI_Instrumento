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

### [2026-10-15] - Smart Track Classification & Piano Lead Extraction (piano_engine.py)
- Implemented `SmartTrackClassifier` in `piano_engine.py`:
  - Intelligent multi-feature analysis (track names, General MIDI program changes, Channel 9/10 percussion detection, and melody pitch register heuristics).
  - Categorizes tracks into roles: `PIANO_LEAD`, `PIANO_ACCOMPANIMENT`, `GUITAR`, `BASS`, `DRUMS`, `OTHER`.
  - Intelligently recognizes when a piece has segmented piano phrases (such as `Studio Grand` tracks 16-28 in `jan gan man.mid`) and groups them into a cohesive **Main Piano Lead**.
- Added `MidiScanner.export_piano_lead_midi`:
  - Automatically isolates and stitches together the piano lead tracks into an individual standalone `.mid` file (e.g. `jan gan man_piano_lead.mid`).
- Upgraded `GrandPianoPlayer` to support:
  - `solo_lead`: Plays purely the Main Piano Lead melody on the Grand Piano.
  - `selected_track_ids`: Allows soloing any specific individual track on the Grand Piano.

### [2026-10-15] - Smart Track CLI Player (play_piano.py)
- Upgraded `play_piano.py` with:
  - Rich interactive track inspection table displaying every detected track with badges (`🎹 Main Piano Lead`, `🎸 Guitar`, `🥁 Drums`), note counts, and pitch ranges.
  - Dedicated playback mode options: Solo Main Piano Lead (recommended), Individual Track Solo, Full Song, and Lead Export.
  - Command-line flags `--lead` (play solo lead directly), `--track <id>` (solo specific track), and `--export-lead` (generate standalone lead `.mid` file).

### [2026-10-15] - Smart Backend API Enhancements (app.py)
- Enhanced `/api/files` to return smart metadata including `lead_notes_count`, `lead_track_ids`, and `is_lead_file`.
- Added `POST /api/export-lead` to trigger on-demand generation and downloading of clean individual Main Piano Lead `.mid` files.
- Upgraded `POST /api/play-native` with `solo_lead` and `selected_track_ids` parameters so Windows hardware MIDI plays the user-selected track or solo lead.

### [2026-10-15] - Smart Track Studio UI (web/index.html & web/style.css)
- Added **Smart Track Mode Switcher** bar directly above visualizer:
  - `Solo Main Piano Lead` tab (primary purpose, enabled by default).
  - `Solo Individual Track` tab (with dynamic track selection dropdown).
  - `All Tracks on Grand Piano` tab.
- Integrated **Smart Track Inspector Modal**:
  - Displays comprehensive table of all detected MIDI tracks with smart roles (`🎹 Main Piano Lead`, `🎸 Guitar`, `🥁 Drums`), note counts, pitch ranges, and instant solo buttons.
- Added **"💾 Export Lead .mid"** one-click export button in header and modal.
- Added corresponding luxury responsive styling in `web/style.css` (modal backdrop, gold highlights, pulse indicators, and track badge styling).

### [2026-10-15] - Smart Client Orchestrator & Lead Renderer (web/piano.js)
- Upgraded `GrandPianoStudio` in `web/piano.js`:
  - Default mode set to `lead` (extracting and playing only the Main Piano Lead melody).
  - Dynamic track filtering based on mode (`lead`, `track`, or `all`).
  - Integrated modal track inspector with direct track soloing.
  - Linked export lead endpoint (`/api/export-lead`) to download individual piano lead `.mid` files and automatically register them in the file list.
  - Added radiant gold color grading and glow particle enhancements in `WaterfallVisualizer` specifically for Main Piano Lead notes.

### [2026-10-15] - Auto-Watch Daemon Lead Optimization (watch_and_play.py)
- Updated `watch_and_play.py` to automatically analyze incoming MIDI files and perform solo Main Piano Lead playback on the Grand Piano with detailed console insights on detected lead notes and tracks.

### [2026-10-15] - Updated Documentation (README.md)
- Updated `README.md` to comprehensively document:
  - Smart Track Identification and melodic phrase grouping.
  - Dedicated Main Piano Lead soloing commands and individual track selection.
  - Lead MIDI export workflow and CLI flags (`--lead`, `--track <id>`, `--export-lead`).
  - Inclusion of the pre-extracted `jan gan man_piano_lead.mid` individual melody file.


















