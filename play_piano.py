import os
import sys
import time
import msvcrt
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
    midi_to_note_name,
    note_is_black_key
)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import BarColumn, Progress, TextColumn
    from rich.live import Live
    from rich.layout import Layout
    from rich.text import Text
    USE_RICH = True
except ImportError:
    USE_RICH = False

console = Console() if USE_RICH else None

def draw_piano_keyboard(active_notes: set, start_octave: int = 2, num_octaves: int = 5) -> str:
    """Renders an ASCII visualization of piano keys across octaves, highlighting active notes."""
    # White keys in an octave: C, D, E, F, G, A, B
    # Note numbers: C=0, D=2, E=4, F=5, G=7, A=9, B=11
    # Black keys: C#=1, D#=3, F#=6, G#=8, A#=10
    
    top_row = []
    bot_row = []
    
    for octv in range(start_octave, start_octave + num_octaves):
        base = (octv + 1) * 12
        notes_in_oct = [
            (base + 0, "C"),
            (base + 1, "C#"),
            (base + 2, "D"),
            (base + 3, "D#"),
            (base + 4, "E"),
            (base + 5, "F"),
            (base + 6, "F#"),
            (base + 7, "G"),
            (base + 8, "G#"),
            (base + 9, "A"),
            (base + 10, "A#"),
            (base + 11, "B"),
        ]
        
        # Build white key representation with black key slots
        # C, C#, D, D#, E, F, F#, G, G#, A, A#, B
        c = "██" if (base + 0) in active_notes else "  "
        cs = "█" if (base + 1) in active_notes else "│"
        d = "██" if (base + 2) in active_notes else "  "
        ds = "█" if (base + 3) in active_notes else "│"
        e = "██" if (base + 4) in active_notes else "  "
        f = "██" if (base + 5) in active_notes else "  "
        fs = "█" if (base + 6) in active_notes else "│"
        g = "██" if (base + 7) in active_notes else "  "
        gs = "█" if (base + 8) in active_notes else "│"
        a = "██" if (base + 9) in active_notes else "  "
        as_ = "█" if (base + 10) in active_notes else "│"
        b = "██" if (base + 11) in active_notes else "  "
        
        # Black keys top row
        b_c_sharp = "■" if (base + 1) in active_notes else "#"
        b_d_sharp = "■" if (base + 3) in active_notes else "#"
        b_f_sharp = "■" if (base + 6) in active_notes else "#"
        b_g_sharp = "■" if (base + 8) in active_notes else "#"
        b_a_sharp = "■" if (base + 10) in active_notes else "#"
        
        top_row.append(f"|{c[:1]}{b_c_sharp}|{d[:1]}{b_d_sharp}|{e}|{f[:1]}{b_f_sharp}|{g[:1]}{b_g_sharp}|{a[:1]}{b_a_sharp}|{b}|")
        bot_row.append(f"|{c}|{d}|{e}|{f}|{g}|{a}|{b}|")

    return "".join(top_row) + "\n" + "".join(bot_row)

def format_time(seconds: float) -> str:
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"

def play_file(file_path: str):
    file_name = os.path.basename(file_path)
    if USE_RICH:
        console.print(f"\n[bold gold1]🎹 Loading Grand Piano Sound Engine for:[/bold gold1] [bold cyan]{file_name}[/bold cyan]")
    else:
        print(f"\nLoading Grand Piano Sound Engine for: {file_name}")

    synth = WindowsMidiSynthesizer()
    if not synth.is_open:
        print("Warning: Windows MIDI device could not be opened.")

    player = GrandPianoPlayer(synth)

    active_notes = set()

    def on_note(pitch, velocity, is_on):
        if is_on:
            active_notes.add(pitch)
        else:
            active_notes.discard(pitch)

    player.on_note_callback = on_note
    player.play(file_path, speed=1.0, force_grand_piano=True)

    header = f"🎹 AI Instrumento - Playing on Grand Piano: {file_name}"
    controls_help = "[Space]: Pause/Resume  |  [+ / -]: Speed  |  [R]: Restart  |  [Q]: Stop & Exit"

    try:
        last_print = 0
        while player.is_playing:
            # Check non-blocking keyboard input on Windows
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch in [b'q', b'Q', b'\x1b']:
                    player.stop()
                    break
                elif ch == b' ':
                    paused = player.toggle_pause()
                    if paused:
                        synth.all_notes_off()
                elif ch in [b'+', b'=']:
                    player.speed = min(3.0, round(player.speed + 0.1, 1))
                elif ch in [b'-', b'_']:
                    player.speed = max(0.2, round(player.speed - 0.1, 1))
                elif ch in [b'r', b'R']:
                    player.stop()
                    player.play(file_path, speed=player.speed, force_grand_piano=True)

            # Update terminal display at ~20 fps
            now = time.time()
            if now - last_print >= 0.05:
                last_print = now
                curr = player.current_time
                total = max(1.0, player.total_duration)
                percent = min(100.0, (curr / total) * 100.0)
                
                bar_len = 30
                filled = int(bar_len * (curr / total))
                prog_bar = "█" * filled + "░" * (bar_len - filled)
                status = "PAUSED" if player.is_paused else f"{player.speed:.1f}x SPEED"

                active_names = sorted([midi_to_note_name(n) for n in active_notes])
                notes_str = ", ".join(active_names) if active_names else "---"

                if USE_RICH:
                    table = Table.grid(padding=1)
                    table.add_row(f"[bold yellow]{header}[/bold yellow]")
                    table.add_row(f"[cyan][{prog_bar}][/cyan] {format_time(curr)} / {format_time(total)} ({percent:5.1f}%) [{status}]")
                    table.add_row(f"[bold green]Active Notes ({len(active_notes)}):[/bold green] [bold white]{notes_str}[/bold white]")
                    table.add_row(f"[dim]{controls_help}[/dim]")
                    
                    # Piano keyboard graphic
                    kb_art = draw_piano_keyboard(active_notes, start_octave=2, num_octaves=4)
                    table.add_row(Panel(f"[yellow]{kb_art}[/yellow]", title="Grand Piano Keys (Octaves C2-B5)"))
                    
                    # Clear screen and print
                    os.system('cls' if os.name == 'nt' else 'clear')
                    console.print(table)
                else:
                    sys.stdout.write(f"\r[{prog_bar}] {format_time(curr)}/{format_time(total)} | Notes: {notes_str[:30]:<30} | {status} ")
                    sys.stdout.flush()

            time.sleep(0.02)

    except KeyboardInterrupt:
        player.stop()
    finally:
        player.stop()
        synth.close()
        print("\nPlayback stopped. Thank you for using AI Instrumento.")


def main():
    directory = "."
    files = MidiScanner.list_midi_files(directory)

    if not files:
        print("\n[!] No .mid or .midi files found in the current directory.")
        print("Please place a MIDI file (e.g. 'jan gan man.mid') in this directory and try again.")
        sys.exit(1)

    # If specified via command line argument
    if len(sys.argv) > 1:
        target = sys.argv[1]
        target_path = Path(target)
        if not target_path.exists():
            target_path = Path(directory) / target
        if not target_path.exists():
            print(f"Error: Specified MIDI file '{target}' not found.")
            sys.exit(1)
        play_file(str(target_path))
        return

    # If only 1 file is present, select it automatically or show menu
    if len(files) == 1:
        print(f"\n[AI Instrumento] Found 1 MIDI file: '{files[0]['name']}'")
        play_file(files[0]["path"])
        return

    # Multiple files present: display menu
    print("\n==========================================")
    print("      🎹 AI INSTRUMENTO - MIDI FILES      ")
    print("==========================================")
    for idx, f in enumerate(files, 1):
        print(f"  [{idx}] {f['name']} ({round(f['size_bytes'] / 1024, 1)} KB)")
    print("==========================================")

    try:
        choice = input(f"Select a file to play on Grand Piano (1-{len(files)}) [Default: 1]: ").strip()
        idx = int(choice) if choice else 1
        if 1 <= idx <= len(files):
            play_file(files[idx - 1]["path"])
        else:
            print("Invalid choice, defaulting to 1.")
            play_file(files[0]["path"])
    except (ValueError, KeyboardInterrupt):
        print("\nExiting.")


if __name__ == "__main__":
    main()
