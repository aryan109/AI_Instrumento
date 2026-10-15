"""
AI Instrumento - Smart Grand Piano MIDI Engine
Provides intelligent MIDI track identification, automatic extraction and solo playback
of the Main Piano Lead, and high-fidelity Acoustic Grand Piano synthesis via Windows Multimedia API (winmm).
"""

import os
import sys
import time
import math
import ctypes
import threading
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any, Set, Tuple

try:
    import mido
except ImportError:
    mido = None

# General MIDI Instrument 0 = Acoustic Grand Piano
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
            return

        try:
            self.winmm = ctypes.windll.winmm
            self.hmidi = ctypes.c_void_p()
            result = self.winmm.midiOutOpen(ctypes.byref(self.hmidi), -1, 0, 0, 0)
            if result == 0:
                self.handle = self.hmidi
                self.is_open = True
                self.reset_all_channels()
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
                # Volume (CC 7) -> 120
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
        except Exception:
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


class SmartTrackClassifier:
    """Intelligently identifies track roles, distinguishes piano leads from accompaniments,
    and groups segmented phrases into a unified Main Piano Lead.
    """
    PIANO_KEYWORDS = ["piano", "grand", "studio grand", "acoustic grand", "keys", "keyboard", "steinway", "yamaha", "upright", "ivory"]
    GUITAR_KEYWORDS = ["guitar", "strum", "acoustic guitar", "electric guitar", "nylon", "steel"]
    BASS_KEYWORDS = ["bass", "upright bass", "fretless", "slap bass"]
    DRUM_KEYWORDS = ["drum", "socal", "percussion", "kit", "hihat", "cymbals", "snare", "kick", "tom"]

    @classmethod
    def classify_track(cls, track_name: str, channel: int, program: Optional[int], notes: List[int]) -> Tuple[str, str, float]:
        """Returns (role, display_badge, lead_confidence_score).
        Roles: 'PIANO_LEAD', 'PIANO_ACCOMPANIMENT', 'GUITAR', 'BASS', 'DRUMS', 'OTHER'
        """
        name_lower = track_name.lower().strip()

        # 1. Channel 9 (MIDI channel 10 zero-indexed) is always drums
        if channel == 9 or any(k in name_lower for k in cls.DRUM_KEYWORDS):
            return "DRUMS", "🥁 Drums/Percussion", 0.0

        # 2. Check for Piano keywords or General MIDI Piano programs (0-7)
        is_piano_named = any(k in name_lower for k in cls.PIANO_KEYWORDS)
        is_piano_program = (program is not None and 0 <= program <= 7)

        # 3. Check for Guitar / Bass keywords
        if any(k in name_lower for k in cls.GUITAR_KEYWORDS):
            return "GUITAR", "🎸 Guitar Accompaniment", 0.1

        if any(k in name_lower for k in cls.BASS_KEYWORDS):
            return "BASS", "🎸 Bass", 0.1

        # Evaluate pitch register for melody lead characteristics
        if notes:
            avg_pitch = sum(notes) / len(notes)
            min_pitch = min(notes)
            max_pitch = max(notes)
        else:
            avg_pitch, min_pitch, max_pitch = 60, 60, 60

        # 4. If identified as Piano:
        if is_piano_named or is_piano_program:
            # Vocal/Melody lead range is typically C4 (60) to C6 (84)
            # Bass/Accompaniment is typically < 55
            if avg_pitch >= 58:
                return "PIANO_LEAD", "🎹 Main Piano Lead", 0.95
            else:
                return "PIANO_ACCOMPANIMENT", "🎹 Piano Accompaniment", 0.7

        # 5. Fallback heuristics for unnamed tracks
        if avg_pitch >= 60 and len(notes) > 5:
            return "PIANO_LEAD", "🎹 Melodic Lead (Piano Candidate)", 0.65

        return "OTHER", "🎵 Instrument", 0.3


class MidiScanner:
    """Scans and analyzes MIDI files with smart track classification,
    timing alignment, and individual Piano Lead extraction.
    """
    @staticmethod
    def list_midi_files(directory: str = ".") -> List[Dict[str, Any]]:
        dir_path = Path(directory)
        midi_files = []
        for p in dir_path.iterdir():
            if p.is_file() and p.suffix.lower() in [".mid", ".midi"]:
                stat = p.stat()
                is_lead_file = "_piano_lead" in p.stem.lower()
                midi_files.append({
                    "name": p.name,
                    "path": str(p.resolve()),
                    "size_bytes": stat.st_size,
                    "modified": stat.st_mtime,
                    "is_lead_file": is_lead_file,
                })
        # Sort so original and newly modified files come first
        midi_files.sort(key=lambda x: (x["is_lead_file"], -x["modified"]))
        return midi_files

    @staticmethod
    def parse_file(file_path: str) -> Dict[str, Any]:
        """Parse MIDI file details, intelligently classifying each track,
        identifying the Main Piano Lead, and generating precise time-indexed notes.
        """
        if mido is None:
            raise RuntimeError("mido library is required to parse MIDI files.")

        mid = mido.MidiFile(file_path)
        tpb = mid.ticks_per_beat

        # 1. Collect all tempo changes to build precise tick_to_second conversion
        tempo_events = [] # (tick, tempo_microseconds)
        for trk in mid.tracks:
            cur_tick = 0
            for msg in trk:
                cur_tick += msg.time
                if msg.type == 'set_tempo':
                    tempo_events.append((cur_tick, msg.tempo))

        tempo_events.sort(key=lambda x: x[0])
        if not tempo_events or tempo_events[0][0] > 0:
            tempo_events.insert(0, (0, 500000))

        def tick_to_sec(tick: int) -> float:
            sec = 0.0
            last_tick = 0
            cur_tempo = 500000
            for t_tick, tempo in tempo_events:
                if tick <= t_tick:
                    break
                sec += mido.tick2second(t_tick - last_tick, tpb, cur_tempo)
                last_tick = t_tick
                cur_tempo = tempo
            sec += mido.tick2second(tick - last_tick, tpb, cur_tempo)
            return sec

        # 2. Analyze and classify each track
        tracks_info = []
        all_notes = []
        piano_lead_track_ids = set()

        for track_id, track in enumerate(mid.tracks):
            track_name = track.name.strip() if track.name else f"Track {track_id}"
            track_notes = []
            channels = set()
            program = None
            active_track_notes = {} # pitch -> (start_sec, vel)
            cur_tick = 0

            for msg in track:
                cur_tick += msg.time
                if hasattr(msg, 'channel'):
                    channels.add(msg.channel)
                if msg.type == 'program_change':
                    program = msg.program

                cur_sec = tick_to_sec(cur_tick)

                if msg.type == 'note_on' and msg.velocity > 0:
                    active_track_notes[msg.note] = (cur_sec, msg.velocity)
                elif (msg.type == 'note_off') or (msg.type == 'note_on' and msg.velocity == 0):
                    if msg.note in active_track_notes:
                        start_sec, vel = active_track_notes.pop(msg.note)
                        dur = max(0.06, cur_sec - start_sec)
                        track_notes.append({
                            "note": msg.note,
                            "name": midi_to_note_name(msg.note),
                            "start": round(start_sec, 3),
                            "duration": round(dur, 3),
                            "velocity": vel,
                            "channel": getattr(msg, 'channel', 0),
                            "track_id": track_id,
                            "track_name": track_name,
                            "is_black": note_is_black_key(msg.note)
                        })

            # Close remaining notes
            for note_pitch, (start_sec, vel) in active_track_notes.items():
                dur = 0.2
                track_notes.append({
                    "note": note_pitch,
                    "name": midi_to_note_name(note_pitch),
                    "start": round(start_sec, 3),
                    "duration": round(dur, 3),
                    "velocity": vel,
                    "channel": list(channels)[0] if channels else 0,
                    "track_id": track_id,
                    "track_name": track_name,
                    "is_black": note_is_black_key(note_pitch)
                })

            if not track_notes:
                continue

            pitches = [n["note"] for n in track_notes]
            channel = list(channels)[0] if channels else 0

            # Smart classification
            role, badge, confidence = SmartTrackClassifier.classify_track(
                track_name=track_name,
                channel=channel,
                program=program,
                notes=pitches
            )

            is_lead = (role == "PIANO_LEAD")
            if is_lead:
                piano_lead_track_ids.add(track_id)

            tracks_info.append({
                "id": track_id,
                "name": track_name,
                "role": role,
                "badge": badge,
                "is_piano_lead": is_lead,
                "confidence": confidence,
                "notes_count": len(track_notes),
                "pitch_min": min(pitches),
                "pitch_max": max(pitches),
                "pitch_avg": round(sum(pitches) / len(pitches), 1),
                "channel": channel,
            })

            # Tag notes with track role
            for n in track_notes:
                n["role"] = role
                n["is_piano_lead"] = is_lead
                all_notes.append(n)

        # If no tracks were classified as piano lead, pick the highest-register melodic track
        if not piano_lead_track_ids and tracks_info:
            best_lead = max(tracks_info, key=lambda t: t["pitch_avg"] if t["role"] != "DRUMS" else -1)
            best_lead["is_piano_lead"] = True
            best_lead["role"] = "PIANO_LEAD"
            best_lead["badge"] = "🎹 Main Piano Lead (Auto-Selected)"
            piano_lead_track_ids.add(best_lead["id"])
            for n in all_notes:
                if n["track_id"] == best_lead["id"]:
                    n["is_piano_lead"] = True
                    n["role"] = "PIANO_LEAD"

        # Sort all notes chronologically
        all_notes.sort(key=lambda x: (x["start"], x["note"]))

        # Count total piano lead notes
        lead_notes = [n for n in all_notes if n["is_piano_lead"]]

        return {
            "file_name": os.path.basename(file_path),
            "file_path": file_path,
            "duration": round(mid.length, 2),
            "total_notes": len(all_notes),
            "lead_notes_count": len(lead_notes),
            "lead_track_ids": list(piano_lead_track_ids),
            "tracks": tracks_info,
            "notes": all_notes,
            "lead_notes": lead_notes,
        }

    @staticmethod
    def export_piano_lead_midi(src_path: str, dst_path: Optional[str] = None) -> str:
        """Extracts all Main Piano Lead notes from the source MIDI file and exports
        a clean, individual standalone MIDI file specifically for the Piano Lead.
        """
        if mido is None:
            raise RuntimeError("mido library is required.")

        src = mido.MidiFile(src_path)
        parsed = MidiScanner.parse_file(src_path)
        lead_track_ids = set(parsed["lead_track_ids"])

        if not dst_path:
            p = Path(src_path)
            dst_path = str(p.parent / f"{p.stem}_piano_lead.mid")

        out = mido.MidiFile(ticks_per_beat=src.ticks_per_beat)

        # Track 0: Tempo and Meta
        meta_trk = mido.MidiTrack()
        meta_trk.name = "Tempo & Time Signature"
        for msg in src.tracks[0]:
            if msg.type in ['set_tempo', 'time_signature', 'key_signature', 'smpte_offset']:
                meta_trk.append(msg.copy())
        out.tracks.append(meta_trk)

        # Track 1: Main Piano Lead (Program 0 = Acoustic Grand Piano)
        lead_trk = mido.MidiTrack()
        lead_trk.name = f"Main Piano Lead - {parsed['file_name']}"
        lead_trk.append(mido.Message('program_change', program=GRAND_PIANO_PROGRAM, channel=0, time=0))

        # Collect notes from lead tracks with absolute ticks
        events = []
        for trk_id in lead_track_ids:
            if trk_id < len(src.tracks):
                cur_tick = 0
                for msg in src.tracks[trk_id]:
                    cur_tick += msg.time
                    if msg.type in ['note_on', 'note_off']:
                        m = msg.copy(channel=0)
                        events.append((cur_tick, m))

        # Sort events by absolute tick
        events.sort(key=lambda x: (x[0], 0 if (x[1].type == 'note_off' or x[1].velocity == 0) else 1))

        last_tick = 0
        for tick, msg in events:
            delta = tick - last_tick
            msg.time = max(0, delta)
            lead_trk.append(msg)
            last_tick = tick

        lead_trk.append(mido.MetaMessage('end_of_track', time=0))
        out.tracks.append(lead_trk)

        out.save(dst_path)
        return dst_path


class GrandPianoPlayer:
    """Handles real-time playback with smart track filtering (e.g. Solo Piano Lead,
    Specific Track Solo, or Full Arrangement) on Acoustic Grand Piano.
    """
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
        self.on_note_callback: Optional[Callable[[int, int, bool, Dict], None]] = None
        self.on_progress_callback: Optional[Callable[[float, float], None]] = None

    def play(
        self,
        file_path: str,
        speed: float = 1.0,
        solo_lead: bool = True,
        selected_track_ids: Optional[List[int]] = None,
        force_grand_piano: bool = True
    ):
        """Start playing MIDI file in background thread."""
        self.stop()
        self.current_file = file_path
        self.speed = speed
        self.stop_requested = False
        self.is_paused = False
        self.is_playing = True

        self._thread = threading.Thread(
            target=self._play_thread,
            args=(file_path, solo_lead, selected_track_ids, force_grand_piano),
            daemon=True
        )
        self._thread.start()

    def _play_thread(
        self,
        file_path: str,
        solo_lead: bool,
        selected_track_ids: Optional[List[int]],
        force_grand_piano: bool
    ):
        if mido is None:
            self.is_playing = False
            return

        try:
            parsed = MidiScanner.parse_file(file_path)
            self.total_duration = parsed["duration"]

            # Determine which notes to play based on user mode
            if selected_track_ids is not None:
                notes_to_play = [n for n in parsed["notes"] if n["track_id"] in selected_track_ids]
            elif solo_lead:
                notes_to_play = parsed["lead_notes"]
            else:
                notes_to_play = parsed["notes"]

            if force_grand_piano:
                self.synth.reset_all_channels()

            # Schedule timeline events
            # Event format: (time_sec, 'on'|'off', note, velocity, note_dict)
            timeline = []
            for n in notes_to_play:
                timeline.append((n["start"], 'on', n["note"], n["velocity"], n))
                timeline.append((n["start"] + n["duration"], 'off', n["note"], 0, n))

            # Sort timeline by time
            timeline.sort(key=lambda x: (x[0], 0 if x[1] == 'off' else 1))

            start_clock = time.perf_counter()
            self.current_time = 0.0

            for event_time, ev_type, pitch, vel, note_info in timeline:
                if self.stop_requested:
                    break

                # Handle pause
                while self.is_paused and not self.stop_requested:
                    time.sleep(0.05)

                # Wait until event time
                target_sleep = (event_time - self.current_time) / max(0.1, self.speed)
                if target_sleep > 0:
                    time.sleep(target_sleep)
                    self.current_time = event_time

                if self.on_progress_callback:
                    self.on_progress_callback(self.current_time, self.total_duration)

                # Send to Windows Grand Piano Synthesizer
                if ev_type == 'on':
                    self.synth.note_on(pitch, vel, channel=0)
                    if self.on_note_callback:
                        self.on_note_callback(pitch, vel, True, note_info)
                else:
                    self.synth.note_off(pitch, 0, channel=0)
                    if self.on_note_callback:
                        self.on_note_callback(pitch, 0, False, note_info)

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
