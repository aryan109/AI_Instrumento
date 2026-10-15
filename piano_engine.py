"""
AI Instrumento - Grand Piano MIDI Engine
Provides high-fidelity MIDI playback on Acoustic Grand Piano via Windows Multimedia API (winmm)
and MIDI file parsing/event extraction.
"""

import os
import sys
import time
import math
import ctypes
import threading
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any

try:
    import mido
except ImportError:
    mido = None

# General MIDI Instrument 0 = Acoustic Grand Piano
# Instrument 1 = Bright Acoustic Piano
GRAND_PIANO_PROGRAM = 0
BRIGHT_PIANO_PROGRAM = 1

# Note naming helper
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

def midi_to_note_name(note_number: int) -> str:
    """Convert MIDI pitch number (0-127) to note name with octave (e.g., 60 -> C4)."""
    octave = (note_number // 12) - 1
    name = NOTE_NAMES[note_number % 12]
    return f"{name}{octave}"

def note_is_black_key(note_number: int) -> bool:
    """Return True if note is a black key (sharp/flat)."""
    semitone = note_number % 12
    return semitone in [1, 3, 6, 8, 10]


class WindowsMidiSynthesizer:
    """Direct Windows Multimedia API (winmm.dll) MIDI Synthesizer.
    Configures channels to General MIDI Acoustic Grand Piano.
    """
    def __init__(self, instrument_program: int = GRAND_PIANO_PROGRAM):
        self.handle = None
        self.instrument_program = instrument_program
        self.is_open = False
        self._lock = threading.Lock()
        self._init_device()

    def _init_device(self):
        if sys.platform != "win32":
            print("[WindowsMidiSynthesizer] Non-windows platform detected, hardware MIDI direct output unavailable.")
            return

        try:
            self.winmm = ctypes.windll.winmm
            self.hmidi = ctypes.c_void_p()
            # Open default MIDI output device (-1: MIDI_MAPPER)
            result = self.winmm.midiOutOpen(ctypes.byref(self.hmidi), -1, 0, 0, 0)
            if result == 0:
                self.handle = self.hmidi
                self.is_open = True
                self.reset_all_channels()
            else:
                print(f"[WindowsMidiSynthesizer] midiOutOpen failed with code {result}")
        except Exception as e:
            print(f"[WindowsMidiSynthesizer] Failed to initialize winmm: {e}")

    def reset_all_channels(self):
        """Set all 16 MIDI channels to Grand Piano and normal volume/pan."""
        if not self.is_open:
            return
        with self._lock:
            for ch in range(16):
                # Program change (0xC0 | ch) -> Grand Piano
                self.send_short_msg(0xC0 | ch, self.instrument_program, 0)
                # Volume (CC 7) -> 127 max
                self.send_cc(ch, 7, 120)
                # Pan (CC 10) -> 64 center
                self.send_cc(ch, 10, 64)
                # Reset all controllers (CC 121)
                self.send_cc(ch, 121, 0)

    def send_short_msg(self, status: int, data1: int, data2: int = 0):
        if not self.is_open:
            return
        msg = (status & 0xFF) | ((data1 & 0xFF) << 8) | ((data2 & 0xFF) << 16)
        try:
            self.winmm.midiOutShortMsg(self.handle, msg)
        except Exception as e:
            pass

    def note_on(self, note: int, velocity: int = 100, channel: int = 0):
        if not (0 <= note <= 127 and 0 <= velocity <= 127):
            return
        self.send_short_msg(0x90 | (channel & 0x0F), note, velocity)

    def note_off(self, note: int, velocity: int = 64, channel: int = 0):
        if not (0 <= note <= 127):
            return
        self.send_short_msg(0x80 | (channel & 0x0F), note, velocity)

    def send_cc(self, channel: int, controller: int, value: int):
        self.send_short_msg(0xB0 | (channel & 0x0F), controller, value)

    def sustain_pedal(self, enable: bool, channel: int = 0):
        """Control sustain damper pedal (CC 64)."""
        val = 127 if enable else 0
        self.send_cc(channel, 64, val)

    def all_notes_off(self):
        """Turn off all ringing notes across all channels."""
        if not self.is_open:
            return
        with self._lock:
            for ch in range(16):
                self.send_cc(ch, 123, 0)  # All Notes Off
                self.send_cc(ch, 64, 0)   # Release sustain pedal

    def close(self):
        if self.is_open and self.handle:
            self.all_notes_off()
            try:
                self.winmm.midiOutClose(self.handle)
            except Exception:
                pass
            self.is_open = False


class MidiScanner:
    """Scans and analyzes MIDI files in directory."""
    @staticmethod
    def list_midi_files(directory: str = ".") -> List[Dict[str, Any]]:
        dir_path = Path(directory)
        midi_files = []
        for p in dir_path.iterdir():
            if p.is_file() and p.suffix.lower() in [".mid", ".midi"]:
                stat = p.stat()
                midi_files.append({
                    "name": p.name,
                    "path": str(p.resolve()),
                    "size_bytes": stat.st_size,
                    "modified": stat.st_mtime,
                })
        # Sort by modification time (newest first)
        midi_files.sort(key=lambda x: x["modified"], reverse=True)
        return midi_files

    @staticmethod
    def parse_file(file_path: str) -> Dict[str, Any]:
        """Parse MIDI file details, tracks, and note events."""
        if mido is None:
            raise RuntimeError("mido library is required to parse MIDI files.")

        mid = mido.MidiFile(file_path)
        tracks_info = []
        notes = []
        tempo_changes = []
        active_notes = {}  # (channel, pitch): (start_sec, vel, track_idx)

        total_time_sec = mid.length

        # Extract track metadata
        for i, track in enumerate(mid.tracks):
            track_name = track.name.strip() if track.name else f"Track {i}"
            is_piano = any(k in track_name.lower() for k in ["piano", "grand", "acoustic"])
            tracks_info.append({
                "id": i,
                "name": track_name,
                "is_piano": is_piano,
                "msg_count": len(track)
            })

        # Calculate absolute timing for all note events
        # We iterate over play events using absolute time
        current_time = 0.0
        for msg in mid:
            current_time += msg.time
            if msg.type == 'note_on' and msg.velocity > 0:
                key = (msg.channel, msg.note)
                active_notes[key] = (current_time, msg.velocity)
            elif (msg.type == 'note_off') or (msg.type == 'note_on' and msg.velocity == 0):
                key = (msg.channel, msg.note)
                if key in active_notes:
                    start_sec, vel = active_notes.pop(key)
                    dur = max(0.05, current_time - start_sec)
                    notes.append({
                        "note": msg.note,
                        "name": midi_to_note_name(msg.note),
                        "start": round(start_sec, 3),
                        "duration": round(dur, 3),
                        "velocity": vel,
                        "channel": msg.channel,
                        "is_black": note_is_black_key(msg.note)
                    })

        # Handle any trailing notes that weren't closed
        for (channel, note), (start_sec, vel) in active_notes.items():
            dur = max(0.1, total_time_sec - start_sec)
            notes.append({
                "note": note,
                "name": midi_to_note_name(note),
                "start": round(start_sec, 3),
                "duration": round(dur, 3),
                "velocity": vel,
                "channel": channel,
                "is_black": note_is_black_key(note)
            })

        # Sort notes by start time
        notes.sort(key=lambda x: (x["start"], x["note"]))

        return {
            "file_name": os.path.basename(file_path),
            "file_path": file_path,
            "duration": round(total_time_sec, 2),
            "total_notes": len(notes),
            "tracks": tracks_info,
            "notes": notes,
        }


class GrandPianoPlayer:
    """Handles real-time playback of a MIDI file on Acoustic Grand Piano."""
    def __init__(self, synth: Optional[WindowsMidiSynthesizer] = None):
        self.synth = synth or WindowsMidiSynthesizer()
        self.is_playing = False
        self.is_paused = False
        self.stop_requested = False
        self.current_time = 0.0
        self.total_duration = 0.0
        self.speed = 1.0
        self.current_file = None
        self._thread = None
        self.on_note_callback: Optional[Callable[[int, int, bool], None]] = None
        self.on_progress_callback: Optional[Callable[[float, float], None]] = None

    def play(self, file_path: str, speed: float = 1.0, force_grand_piano: bool = True):
        """Start playing MIDI file in background thread."""
        self.stop()
        self.current_file = file_path
        self.speed = speed
        self.stop_requested = False
        self.is_paused = False
        self.is_playing = True

        self._thread = threading.Thread(
            target=self._play_thread,
            args=(file_path, force_grand_piano),
            daemon=True
        )
        self._thread.start()

    def _play_thread(self, file_path: str, force_grand_piano: bool):
        if mido is None:
            print("mido is not installed")
            self.is_playing = False
            return

        try:
            mid = mido.MidiFile(file_path)
            self.total_duration = mid.length
            if force_grand_piano:
                self.synth.reset_all_channels()

            self.current_time = 0.0
            start_clock = time.perf_counter()

            for msg in mid:
                if self.stop_requested:
                    break

                # Handle pause
                while self.is_paused and not self.stop_requested:
                    time.sleep(0.05)

                # Sleep delta time adjusted for playback speed
                delta = msg.time / max(0.1, self.speed)
                if delta > 0:
                    time.sleep(delta)
                    self.current_time += msg.time

                if self.on_progress_callback:
                    self.on_progress_callback(self.current_time, self.total_duration)

                # Send message to Windows synthesizer
                if msg.type == 'note_on':
                    # If force_grand_piano is on, channel is mapped or channel program kept 0
                    if force_grand_piano:
                        # Ensure voice stays grand piano
                        self.synth.send_short_msg(0xC0 | msg.channel, GRAND_PIANO_PROGRAM, 0)

                    if msg.velocity > 0:
                        self.synth.note_on(msg.note, msg.velocity, channel=msg.channel)
                        if self.on_note_callback:
                            self.on_note_callback(msg.note, msg.velocity, True)
                    else:
                        self.synth.note_off(msg.note, 0, channel=msg.channel)
                        if self.on_note_callback:
                            self.on_note_callback(msg.note, 0, False)

                elif msg.type == 'note_off':
                    self.synth.note_off(msg.note, msg.velocity, channel=msg.channel)
                    if self.on_note_callback:
                        self.on_note_callback(msg.note, 0, False)

                elif msg.type == 'control_change':
                    # Support sustain pedal & volume
                    self.synth.send_cc(msg.channel, msg.control, msg.value)

        except Exception as e:
            print(f"[GrandPianoPlayer] Playback error: {e}")
        finally:
            self.synth.all_notes_off()
            self.is_playing = False
            self.is_paused = False

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        return self.is_paused

    def stop(self):
        self.stop_requested = True
        self.is_playing = False
        self.is_paused = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        self.synth.all_notes_off()
