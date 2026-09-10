#!/usr/bin/env python3
"""Bake-off comparator and gate for the two renderers.

    python3 compare.py                      # render both, compare, report
    python3 compare.py --negative-control   # prove the editability check can fail

The claim being tested is not "did a file appear". It is:

  1. Both decks carry the SAME content, so we are comparing renderers rather than
     two different readings of one outline.
  2. Charts are NATIVE chart parts (ppt/charts/chart*.xml), not pictures. This is
     the whole reason Marp was rejected: its default pptx export bakes each slide
     to a background image, so nothing can be edited or interrogated afterwards.
  3. Body text is real text in the slide XML, so it is editable in PowerPoint.

Exit 0 = PASS. Exit 1 = FAIL, loud, with each failure named.
"""

import argparse
import importlib.util
import pathlib
import re
import subprocess
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"

_spec = importlib.util.spec_from_file_location("outline_parser", HERE / "outline-parser.py")
outline_parser = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(outline_parser)


def probe(path: pathlib.Path):
    """Structural facts about a .pptx, read from the OOXML package itself."""
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        slides = [n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
        charts = [n for n in names if re.fullmatch(r"ppt/charts/chart\d+\.xml", n)]
        notes = [n for n in names if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", n)]
        # Real picture parts only. PptxGenJS writes a zero-byte "ppt/media/" DIRECTORY
        # entry even with no images; counting it read as a rasterised chart and was a
        # false positive in this gate's first cut.
        media = [n for n in names
                 if n.startswith("ppt/media/") and not n.endswith("/")
                 and z.getinfo(n).file_size > 0]
        text = []
        for s in sorted(slides):
            xml = z.read(s).decode("utf8", "replace")
            text.extend(re.findall(r"<a:t>(.*?)</a:t>", xml, re.S))
        notes_text = []
        for n in sorted(notes):
            xml = z.read(n).decode("utf8", "replace")
            notes_text.extend(re.findall(r"<a:t>(.*?)</a:t>", xml, re.S))
    return {
        "path": path,
        "slides": len(slides),
        "charts": len(charts),
        # PptxGenJS emits a notes slide for EVERY slide, carrying only the slide
        # number when there is no note. Count the ones with real content instead,
        # so the two renderers are compared on substance rather than on packaging.
        "notes": sum(1 for t in notes_text if len(t.strip()) > 5),
        "media": len(media),
        "runs": len(text),
        "text": " ".join(text),
        "notesText": " ".join(notes_text),
        "bytes": path.stat().st_size,
    }


def render_both():
    subprocess.run([sys.executable, str(HERE / "render-python-pptx.py"),
                    str(HERE / "sample-outline.md"), "-o", str(OUT / "python-pptx.pptx")],
                   check=True, cwd=HERE, stdout=subprocess.DEVNULL)
    subprocess.run(["node", str(HERE / "render-pptxgenjs.js"),
                    str(HERE / "sample-outline.md"), "-o", str(OUT / "pptxgenjs.pptx")],
                   check=True, cwd=HERE, stdout=subprocess.DEVNULL)


def check(a, b, deck):
    fails = []
    expected_slides = len(deck["slides"]) + 1
    expected_charts = sum(1 for s in deck["slides"] for x in s["blocks"] if x["kind"] == "chart")
    expected_notes = sum(1 for s in deck["slides"] if s["notes"])

    for r in (a, b):
        tag = r["path"].name
        if r["slides"] != expected_slides:
            fails.append(f"{tag}: {r['slides']} slides, outline implies {expected_slides}")
        if r["charts"] != expected_charts:
            fails.append(f"{tag}: {r['charts']} NATIVE chart parts, outline implies {expected_charts}")
        if r["notes"] != expected_notes:
            fails.append(f"{tag}: {r['notes']} notes slides, outline implies {expected_notes}")
        if r["media"] > 0:
            fails.append(f"{tag}: {r['media']} embedded media; charts should be native, not pictures")
        if r["runs"] < 20:
            fails.append(f"{tag}: only {r['runs']} text runs; body text may be rasterised")

    # Same content out of both renderers: every bullet and every speaker note must
    # survive in both decks. Presence beats counting; counting is what produced this
    # gate's two false positives on the first run.
    for s in deck["slides"]:
        for blk in s["blocks"]:
            if blk["kind"] != "bullet":
                continue
            probe_text = blk["text"][:40]
            for r in (a, b):
                if probe_text not in r["text"]:
                    fails.append(f"{r['path'].name}: bullet missing from slide XML: {probe_text!r}")
        if s["notes"]:
            probe_note = s["notes"][:40]
            for r in (a, b):
                if probe_note not in r["notesText"]:
                    fails.append(f"{r['path'].name}: speaker note missing: {probe_note!r}")
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--negative-control", action="store_true")
    args = ap.parse_args()

    render_both()
    deck = outline_parser.parse(HERE / "sample-outline.md")
    a = probe(OUT / "python-pptx.pptx")
    b = probe(OUT / "pptxgenjs.pptx")

    if args.negative_control:
        # Strip the chart parts from one deck and confirm the gate notices. This is
        # the exact failure mode Marp would exhibit, simulated.
        victim = OUT / "negative-control.pptx"
        with zipfile.ZipFile(OUT / "python-pptx.pptx") as z, zipfile.ZipFile(victim, "w") as w:
            for n in z.namelist():
                if re.fullmatch(r"ppt/charts/chart\d+\.xml", n):
                    continue
                w.writestr(n, z.read(n))
        red = check(probe(victim), b, deck)
        victim.unlink()
        chart_fails = [f for f in red if "NATIVE chart" in f]
        if chart_fails:
            print("NEGATIVE CONTROL PASS: removing chart parts turned the gate red.")
            print("  " + chart_fails[0])
            return 0
        print("NEGATIVE CONTROL FAIL: gate stayed green with charts removed.")
        return 1

    hdr = f"{'':<22}{'python-pptx':>14}{'pptxgenjs':>14}"
    print(hdr)
    print("-" * len(hdr))
    for k, label in [("slides", "slides"), ("charts", "native charts"),
                     ("notes", "notes slides"), ("media", "embedded images"),
                     ("runs", "text runs"), ("bytes", "bytes")]:
        print(f"{label:<22}{a[k]:>14,}{b[k]:>14,}")

    fails = check(a, b, deck)
    print()
    if fails:
        print("FAIL")
        for f in fails:
            print("  - " + f)
        return 1
    print("PASS: both decks match the outline, charts are native, text is editable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
