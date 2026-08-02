"""
Archive and reset a bot's SIM book + equity curve.

WHY YOU NEED THIS: the momentum and reversion bots had a bug where exit orders
were silently dropped — positions accumulated without bound and each stranded
position was marked at its entry cost forever, freezing its P&L at zero. The
options bot had a parallel bug where every risk cap was inert in SIM, so its
book grew by up to 10 spreads per day.

Curves produced before those fixes are not salvageable and not correctable
after the fact. Every Sharpe, vol and correlation computed from them is wrong.
The only honest move is to archive them and start clean.

Usage (on the Oracle box, from ~/quant_bots with the venv active):

    # Look before you leap — shows what would be archived, changes nothing
    python scripts/reset_sim_curves.py --bots momentum reversion options --dry-run

    # Do it
    python scripts/reset_sim_curves.py --bots momentum reversion options

    # Then restart so the bots rebuild from an empty book
    sudo systemctl restart momentum-bot reversion-bot options-bot

Nothing is deleted. Everything is moved to data/sim/_archive/<bot>_<stamp>/ in
case you want to inspect the damage later.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

ALL_BOTS = ("trend", "momentum", "reversion", "options")


def describe(sim_dir: Path) -> str:
    if not sim_dir.exists():
        return "no sim data"
    curve = sim_dir / "equity_curve.jsonl"
    days = 0
    if curve.exists():
        days = sum(1 for line in curve.read_text().splitlines() if line.strip())
    files = sorted(p.name for p in sim_dir.iterdir() if p.is_file())
    return f"{days} curve rows, files: {', '.join(files) or 'none'}"


def reset_bot(project_root: Path, bot: str, dry_run: bool, stamp: str) -> bool:
    sim_dir = project_root / "data" / "sim" / bot
    if not sim_dir.exists() or not any(sim_dir.iterdir()):
        print(f"  {bot:<10} nothing to reset")
        return False

    print(f"  {bot:<10} {describe(sim_dir)}")
    if dry_run:
        print(f"  {'':<10} would archive -> data/sim/_archive/{bot}_{stamp}/")
        return False

    archive = project_root / "data" / "sim" / "_archive" / f"{bot}_{stamp}"
    archive.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(sim_dir), str(archive))
    sim_dir.mkdir(parents=True, exist_ok=True)
    print(f"  {'':<10} archived -> {archive.relative_to(project_root)}")
    return True


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bots", nargs="+", default=["momentum", "reversion", "options"],
                   choices=list(ALL_BOTS),
                   help="which bots to reset (default: the three affected by the bugs)")
    p.add_argument("--dry-run", action="store_true",
                   help="show what would happen, change nothing")
    p.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    args = p.parse_args()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "DRY RUN — nothing will change" if args.dry_run else "RESETTING"
    print(f"{mode}\nProject root: {args.project_root}\n")

    reset_count = sum(reset_bot(args.project_root, b, args.dry_run, stamp)
                      for b in args.bots)

    print()
    if args.dry_run:
        print("Re-run without --dry-run to apply.")
    elif reset_count:
        print(f"Reset {reset_count} bot(s). Now restart them so they rebuild "
              f"from an empty book:\n")
        print(f"  sudo systemctl restart {' '.join(b + '-bot' for b in args.bots)}\n")
        print("Correlations need ~20+ overlapping days to mean anything, so the "
              "tracker will (correctly) warn for the first few weeks.")
    else:
        print("Nothing needed resetting.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
