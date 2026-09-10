#!/usr/bin/env python3
"""One entrypoint: pull local calendar -> dedupe -> render -> HTML.

    python3 build.py --view week            # fixed Sun..Sat containing today
    python3 build.py --view rolling         # today .. +6 days
    python3 build.py --view week --ref 2026-07-15 --open

Pulls a generous date range (ref-7 .. ref+9) so either view is fully covered,
then lets render.py select and lay out its own window. The pull is the only
step that touches macOS; if Calendar access is not granted it exits with clear
setup instructions (see SKILL.md > First-run setup).
"""
import argparse
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import dedupe as dedupe_mod
import render as render_mod

HERE = Path(__file__).resolve().parent
PULL = HERE / "pull.js"
CONFIG = HERE.parent / "config.json"

# Output lands in the user's own Documents, never inside the skill folder: the
# skill lives in the clone (~/rjsTools), which reinstalls and resets delete. A
# calendar the user built should outlive the tool that built it, and nobody
# thinks to look for their week inside a scripts directory.
OUTDIR = Path.home() / "Documents" / "calPreview"


def load_config() -> dict:
    if CONFIG.exists():
        return json.loads(CONFIG.read_text())
    return {}


def _capture(step: str, detail: str) -> None:
    """Auto-write a delivery report so any install-time failure produces the
    hand-back file without the user remembering to run the doctor."""
    try:
        subprocess.run([sys.executable, str(HERE / "doctor.py"),
                        "--record-failure", step, detail[:500]],
                       capture_output=True, text=True, timeout=90)
        sys.stderr.write("  (a deliveryReport was written — share it back to improve the installer)\n")
    except Exception:  # noqa: BLE001
        pass


def pull(start: date, end: date) -> list:
    """Run the JXA EventKit pull; return the raw event list or exit loudly."""
    proc = subprocess.run(
        ["osascript", "-l", "JavaScript", str(PULL), start.isoformat(), end.isoformat()],
        capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        _capture("calendar pull", f"rc={proc.returncode}; {proc.stderr.strip()}")
        sys.exit("ERROR: calendar pull failed (see message above). "
                 "If this is a permission error, grant Calendar access to the "
                 "app running this, then retry — see SKILL.md.")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        _capture("calendar pull", "pull returned non-JSON output")
        sys.exit(f"ERROR: pull did not return JSON. stderr:\n{proc.stderr}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--view", default="week", choices=["week", "rolling"])
    ap.add_argument("--ref", default=None, help="reference date YYYY-MM-DD (default today)")
    ap.add_argument("--out", default=None, help="output HTML path")
    ap.add_argument("--open", action="store_true", help="open the HTML when done")
    a = ap.parse_args()

    ref = date.fromisoformat(a.ref) if a.ref else date.today()
    cfg = load_config()
    raw = pull(ref - timedelta(days=7), ref + timedelta(days=9))
    result = dedupe_mod.dedupe(raw, cfg.get("personalCalendars", []))
    st = result["stats"]
    sys.stderr.write(f"pulled {st['raw']} raw -> {st['unique']} unique "
                     f"({st['merged']} join-holds merged)\n")

    out = Path(a.out).expanduser() if a.out else (
        OUTDIR / f"calPreview_{a.view}_{ref.isoformat()}.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_mod.render(result["events"], a.view, ref))
    print(out)
    sys.stderr.write("saved. To keep a PDF: open it, press ⌘P, "
                     "then \"Save as PDF\" (it is laid out to print landscape).\n")
    if a.open:
        subprocess.run(["open", str(out)])


if __name__ == "__main__":
    main()
