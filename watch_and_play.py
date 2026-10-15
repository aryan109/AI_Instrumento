import os
import sys
import time
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from piano_engine import (
    WindowsMidiSynthesizer,
    GrandPianoPlayer,
    MidiScanner,
    midi_to_note_name
)

WATCH_DIR = Path(".")

def main():
    print("=" * 60)
    print("   [PIANO] AI INSTRUMENTO - AUTO WATCH & GRAND PIANO DAEMON   ")
    print("=" * 60)
    print(f" Watching directory: {WATCH_DIR.resolve()}")
    print(" Whenever a .mid file is detected or added, it will play")
    print(" on the Acoustic Grand Piano automatically.")
    print(" Press Ctrl+C to terminate.")
    print("=" * 60)

    synth = WindowsMidiSynthesizer()
    player = GrandPianoPlayer(synth)

    processed_files = set()

    def play_midi(fpath):
        fname = os.path.basename(fpath)
        print(f"\n[▶ PLAYING] Starting Grand Piano performance for: '{fname}'")
        try:
            player.play(fpath, speed=1.0, force_grand_piano=True)
            while player.is_playing:
                time.sleep(0.5)
            print(f"[✔ FINISHED] Finished playing '{fname}'.")
        except KeyboardInterrupt:
            player.stop()
            raise
        except Exception as e:
            print(f"[!] Playback error: {e}")

    try:
        # Check initial files
        existing = MidiScanner.list_midi_files(str(WATCH_DIR))
        if existing:
            print(f"\nFound {len(existing)} existing MIDI file(s):")
            for idx, ef in enumerate(existing, 1):
                print(f"  [{idx}] {ef['name']}")
                processed_files.add(ef['path'])

            # Play the first existing one
            play_midi(existing[0]['path'])

        print("\n[👁 WATCHING] Listening for newly added .mid files in directory...")
        while True:
            current_files = MidiScanner.list_midi_files(str(WATCH_DIR))
            for cf in current_files:
                path = cf['path']
                if path not in processed_files:
                    print(f"\n[★ NEW FILE DETECTED] '{cf['name']}' was added to directory!")
                    processed_files.add(path)
                    play_midi(path)
                    print("\n[👁 WATCHING] Listening for newly added .mid files...")

            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\nStopping Auto-Watch Daemon.")
    finally:
        player.stop()
        synth.close()


if __name__ == "__main__":
    main()
