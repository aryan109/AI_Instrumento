import os
import sys
import time
import msvcrt
import argparse
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
    USE_RICH = True
except ImportError:
    USE_RICH = False

console = Console() if USE_RICH else None

def draw_piano_keyboard(active_notes: set, start_octave: int = 2, num_octaves: int = 4) -> str:
    """Renders an ASCII visualization of piano keys across octaves, highlighting active notes."""
    top_row = []
    bot_row = []
    
    for octv in range(start_octave, start_octave + num_octaves):
        base = (octv + 1) * 12
        c = "██" if (base + 0) in active_notes else "  "
        d = "██" if (base + 2) in active_notes else "  "
        e = "██" if (base + 4) in active_notes else "  "
        f = "██" if (base + 5) in active_notes else "  "
        g = "██" if (base + 7) in active_notes else "  "
        a = "██" if (base + 9) in active_notes else "  "
        b = "██" if (base + 11) in active_notes else "  "
        
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

def play_file(file_path: str, solo_lead: bool = True, selected_track_ids: list = None):
    file_name = os.path.basename(file_path)
    parsed = MidiScanner.parse_file(file_path)

    mode_title = "Solo Main Piano Lead" if solo_lead else (
        f"Track {selected_track_ids[0]} Solo" if selected_track_ids else "All Tracks on Grand Piano"
    )

    if USE_RICH:
        console.print(f"\n[bold gold1]🎹 Grand Piano Engine:[/bold gold1] [bold cyan]{file_name}[/bold cyan] ([bold yellow]{mode_title}[/bold yellow])")
    else:
        print(f"\nGrand Piano Engine: {file_name} ({mode_title})")

    synth = WindowsMidiSynthesizer()
    if not synth.is_open:
        print("Warning: Windows MIDI device could not be opened.")

    player = GrandPianoPlayer(synth)

    active_notes = set()

    def on_note(pitch, velocity, is_on, note_info):
        if is_on:
            active_notes.add(pitch)
        else:
            active_notes.discard(pitch)

    player.on_note_callback = on_note
    player.play(
        file_path,
        speed=1.0,
        solo_lead=solo_lead,
        selected_track_ids=selected_track_ids,
        force_grand_piano=True
    )

    header = f"🎹 AI Instrumento - Grand Piano: {file_name} [{mode_title}]"
    controls_help = "[Space]: Pause/Resume  |  [+ / -]: Speed  |  [R]: Restart  |  [Q]: Stop & Exit"

    try:
        last_print = 0
        while player.is_playing:
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
                    player.play(
                        file_path,
                        speed=player.speed,
                        solo_lead=solo_lead,
                        selected_track_ids=selected_track_ids,
                        force_grand_piano=True
                    )

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
                    
                    kb_art = draw_piano_keyboard(active_notes, start_octave=2, num_octaves=4)
                    table.add_row(Panel(f"[yellow]{kb_art}[/yellow]", title="Grand Piano Keys (Octaves C2-B5)"))
                    
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


def show_track_inspection(file_path: str):
    parsed = MidiScanner.parse_file(file_path)
    if USE_RICH:
        table = Table(title=f"Smart MIDI Track Identification: {parsed['file_name']}", border_style="gold1")
        table.add_column("Track ID", justify="right", style="cyan")
        table.add_column("Track Name", style="white")
        table.add_column("Role / Badge", style="bold green")
        table.add_column("Notes", justify="right", style="yellow")
        table.add_column("Pitch Range", style="magenta")
        table.add_column("Lead Status", style="bold gold1")

        for t in parsed["tracks"]:
            is_lead_str = "★ MAIN LEAD" if t["is_piano_lead"] else "Accompaniment"
            range_str = f"{midi_to_note_name(t['pitch_min'])} - {midi_to_note_name(t['pitch_max'])} (avg {t['pitch_avg']})"
            table.add_row(
                str(t["id"]),
                t["name"],
                t["badge"],
                str(t["notes_count"]),
                range_str,
                is_lead_str
            )
        console.print(table)
        console.print(f"[bold gold1]Identified Main Piano Lead:[/bold gold1] {parsed['lead_notes_count']} total lead notes across {len(parsed['lead_track_ids'])} track phrase(s).")
    else:
        print(f"\nSmart MIDI Track Identification: {parsed['file_name']}")
        print("-" * 75)
        for t in parsed["tracks"]:
            lead_tag = " [MAIN LEAD]" if t["is_piano_lead"] else ""
            print(f"Track {t['id']:2d}: {t['name']:<20} | {t['badge']:<22} | Notes: {t['notes_count']:4d} | Range: {t['pitch_min']}-{t['pitch_max']}{lead_tag}")
        print(f"Total Piano Lead notes: {parsed['lead_notes_count']}")


def main():
    parser = argparse.ArgumentParser(description="AI Instrumento - Smart Grand Piano MIDI Player")
    parser.add_argument("file", nargs="?", help="MIDI file path to play")
    parser.add_argument("--lead", action="store_true", help="Play only the Main Piano Lead")
    parser.add_argument("--all", action="store_true", help="Play all tracks on Grand Piano")
    parser.add_argument("--track", type=int, help="Play specific track ID solo")
    parser.add_argument("--export-lead", action="store_true", help="Export Main Piano Lead to standalone .mid file")
    args = parser.parse_args()

    directory = "."
    files = MidiScanner.list_midi_files(directory)

    if not files:
        print("\n[!] No .mid or .midi files found in the current directory.")
        sys.exit(1)

    # Determine file
    target_path = None
    if args.file:
        target_path = Path(args.file)
        if not target_path.exists():
            target_path = Path(directory) / args.file
        if not target_path.exists():
            print(f"Error: Specified MIDI file '{args.file}' not found.")
            sys.exit(1)
    else:
        # Pick default: prefer jan gan man.mid or lead file or first file
        lead_cand = [f for f in files if "jan gan man" in f["name"].lower() and not f["is_lead_file"]]
        target_path = Path(lead_cand[0]["path"]) if lead_cand else Path(files[0]["path"])

    # Export lead option
    if args.export_lead:
        out_file = MidiScanner.export_piano_lead_midi(str(target_path))
        print(f"\n[✔] Main Piano Lead exported successfully to: '{out_file}'")
        return

    # Direct flag playback
    if args.lead:
        play_file(str(target_path), solo_lead=True)
        return
    elif args.all:
        play_file(str(target_path), solo_lead=False)
        return
    elif args.track is not None:
        play_file(str(target_path), solo_lead=False, selected_track_ids=[args.track])
        return

    # Interactive Menu
    show_track_inspection(str(target_path))

    print("\n" + "=" * 50)
    print("      🎹 SELECT GRAND PIANO PLAYBACK MODE        ")
    print("=" * 50)
    print("  [1] ★ Play Solo Main Piano Lead (RECOMMENDED) ")
    print("  [2] 🎛 Play Specific Individual Track Solo    ")
    print("  [3] 🎹 Play All Tracks on Grand Piano         ")
    print("  [4] 💾 Export Piano Lead to Standalone .mid   ")
    print("  [5] 📂 Switch to another MIDI file            ")
    print("=" * 50)

    try:
        choice = input("Enter choice (1-5) [Default: 1]: ").strip() or "1"
        if choice == "1":
            play_file(str(target_path), solo_lead=True)
        elif choice == "2":
            trk_str = input("Enter Track ID to solo (e.g. 16): ").strip()
            try:
                trk_id = int(trk_str)
                play_file(str(target_path), solo_lead=False, selected_track_ids=[trk_id])
            except ValueError:
                print("Invalid track ID.")
        elif choice == "3":
            play_file(str(target_path), solo_lead=False)
        elif choice == "4":
            out_file = MidiScanner.export_piano_lead_midi(str(target_path))
            print(f"\n[✔] Exported to '{out_file}'. Playing exported lead now...")
            play_file(out_file, solo_lead=False)
        elif choice == "5":
            for idx, f in enumerate(files, 1):
                print(f"  [{idx}] {f['name']}")
            f_idx = int(input(f"Select file (1-{len(files)}): ").strip())
            play_file(files[f_idx - 1]["path"], solo_lead=True)
    except (ValueError, KeyboardInterrupt):
        print("\nExiting.")


if __name__ == "__main__":
    main()
