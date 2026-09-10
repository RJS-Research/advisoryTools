#!/usr/bin/env python3
"""Shared parser for the deck outline dialect.

Both renderers consume this, so a bake-off compares RENDERERS rather than two
different readings of the same file. Imported by render-python-pptx.py and dumped
to JSON for render-pptxgenjs.js via `--json`.

Dialect:
    # Title              deck title slide; `subtitle:` / `footer:` lines follow
    ## Slide title       starts a content slide
    - bullet             one body bullet
    ```chart {json}```   a native chart
    > note               speaker note, appended to the current slide
    <!-- ... -->         ignored
"""

import json
import pathlib
import re
import sys


def parse(path):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)

    deck = {"title": None, "subtitle": None, "footer": None, "slides": []}
    cur = None
    in_chart = False
    chart_buf = []

    for raw in text.splitlines():
        line = raw.rstrip()

        if in_chart:
            if line.strip().startswith("```"):
                in_chart = False
                spec = json.loads("\n".join(chart_buf))
                if cur is None:
                    raise ValueError("chart block before any '## ' slide heading")
                cur["blocks"].append({"kind": "chart", "spec": spec})
                chart_buf = []
            else:
                chart_buf.append(line)
            continue

        if line.strip().startswith("```chart"):
            in_chart = True
            continue

        if line.startswith("# "):
            deck["title"] = line[2:].strip()
        elif line.startswith("## "):
            cur = {"title": line[3:].strip(), "blocks": [], "notes": []}
            deck["slides"].append(cur)
        elif line.startswith("- "):
            if cur is None:
                raise ValueError("bullet before any '## ' slide heading")
            cur["blocks"].append({"kind": "bullet", "text": line[2:].strip()})
        elif line.startswith("> "):
            target = cur["notes"] if cur else []
            target.append(line[2:].strip())
        elif line.lower().startswith("subtitle:") and deck["subtitle"] is None:
            deck["subtitle"] = line.split(":", 1)[1].strip()
        elif line.lower().startswith("footer:") and deck["footer"] is None:
            deck["footer"] = line.split(":", 1)[1].strip()

    if in_chart:
        raise ValueError("unterminated ```chart block")
    if deck["title"] is None:
        raise ValueError("no '# ' deck title found")

    # Join wrapped speaker-note lines into one paragraph per slide.
    for s in deck["slides"]:
        s["notes"] = " ".join(s["notes"]).strip()
    return deck


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "sample-outline.md"
    print(json.dumps(parse(src), indent=2))
