#!/usr/bin/env python3
"""Render deduped events into a brand-styled weekly calendar (HTML).

Two views (Rob's spec):
  week     — a fixed Sun..Sat calendar week containing the reference date.
  rolling  — the reference date through the next 6 days (7 columns), with
             weekend columns highlighted.

Browser-only deliverable, so it uses absolute-positioned minute-precise blocks
(not the email-safe rowspan table the FSC availability sheet needs). Palette and
type mirror brandStandards.md.

Importable: render(events, view, ref_date) -> html. Also a CLI (stdin = the
dedupe.py object {events,...} or a bare events array).
"""
import argparse
import json
import sys
from datetime import date, datetime, timedelta

# --- brand palette (brandStandards.md) ---
FOREST = "#004000"; MOSS = "#4A6B3A"; OLIVE = "#A8A47C"; INK = "#222222"
SUB = "#444444"; HAIRLINE = "#DCE3D6"; HAIR_STRONG = "#B9C4B0"; GUTTER = "#8A9683"
WIN_FILL = "#E9EFE1"; WIN_BORDER = "#4A6B3A"; WIN_INK = "#004000"; LOC_INK = "#6C8560"
PERS_FILL = "#F4F1E6"; PERS_BORDER = "#A8A47C"; PERS_INK = "#6B6636"
OFF_FILL = "#F1F3EE"; TODAY_TOP = "#4A6B3A"

PXMIN = 1.0            # 1px per minute
COLW = 132
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _clock(mins: int) -> str:
    h, m = divmod(mins, 60)
    h12 = ((h - 1) % 12) + 1
    ap = "AM" if h < 12 else "PM"
    return f"{h12}:{m:02d} {ap}" if m else f"{h12} {ap}"


def _clock_range(a: int, b: int) -> str:
    return f"{_clock(a)} – {_clock(b)}"


def _parse(dt: str) -> datetime:
    return datetime.fromisoformat(dt)


def _cols_for(view: str, ref: date):
    if view == "week":
        sun = ref - timedelta(days=(ref.weekday() + 1) % 7)   # Mon=0..Sun=6
        return [sun + timedelta(days=i) for i in range(7)]
    if view == "rolling":
        return [ref + timedelta(days=i) for i in range(7)]
    raise SystemExit(f"ERROR: unknown view '{view}' (use week|rolling)")


def _lanes(day_events):
    """Greedy interval colouring -> (event, lane, n_lanes) so overlaps sit
    side-by-side instead of stacking on top of each other."""
    lane_end = []                         # last end-minute per lane
    placed = []
    for e in sorted(day_events, key=lambda x: (x["_s"], x["_e"])):
        lane = next((i for i, end in enumerate(lane_end) if end <= e["_s"]), None)
        if lane is None:
            lane = len(lane_end)
            lane_end.append(e["_e"])
        else:
            lane_end[lane] = e["_e"]
        placed.append([e, lane])
    n = max((l for _, l in placed), default=-1) + 1
    return [(e, lane, n) for e, lane in placed]


def render(events: list, view: str, ref: date) -> str:
    cols = _cols_for(view, ref)
    today = date.today()

    # bucket events by column date; split timed vs all-day; clamp to grid
    by_day = {c: {"timed": [], "allday": []} for c in cols}
    for e in events:
        s = _parse(e["start"])
        d = s.date()
        if d not in by_day:
            continue
        if e.get("allDay"):
            by_day[d]["allday"].append(e)
        else:
            en = _parse(e["end"])
            rec = dict(e, _s=s.hour * 60 + s.minute,
                       _e=max(en.hour * 60 + en.minute, s.hour * 60 + s.minute + 20)
                       if en.date() == d else 24 * 60)
            by_day[d]["timed"].append(rec)

    # dynamic vertical bounds from the timed events actually shown
    starts = [r["_s"] for c in cols for r in by_day[c]["timed"]]
    ends = [r["_e"] for c in cols for r in by_day[c]["timed"]]
    if starts:
        gmin = (min(starts) // 60) * 60
        gmax = -(-max(ends) // 60) * 60          # ceil to hour
        gmin, gmax = min(gmin, 9 * 60), max(gmax, 17 * 60)
    else:
        gmin, gmax = 9 * 60, 17 * 60
    grid_h = int((gmax - gmin) * PXMIN)
    hours = list(range(gmin // 60, gmax // 60 + 1))

    def block(rec, lane, n):
        top = int((rec["_s"] - gmin) * PXMIN)
        h = int((rec["_e"] - rec["_s"]) * PXMIN)
        if rec["kind"] == "work":
            fill, bord, tint = WIN_FILL, WIN_BORDER, LOC_INK
        else:
            fill, bord, tint = PERS_FILL, PERS_BORDER, PERS_INK
        ink = WIN_INK if rec["kind"] == "work" else PERS_INK
        w = 100.0 / n
        left = lane * w
        links = "".join(
            f'<div style="font-size:9px;font-weight:bold;text-transform:uppercase;'
            f'letter-spacing:0.04em;color:{tint};margin-top:2px;">▶ {_esc(l)}</div>'
            for l in rec.get("links", []))
        return (
            f'<div style="position:absolute;top:{top}px;height:{h}px;'
            f'left:calc({left}% + 2px);width:calc({w}% - 4px);box-sizing:border-box;'
            f'background:{fill};border-left:3px solid {bord};border-radius:2px;'
            f'padding:3px 5px;overflow:hidden;">'
            f'<div style="font-size:11px;color:{ink};font-weight:bold;">{_clock_range(rec["_s"], rec["_e"])}</div>'
            f'<div style="font-size:11px;color:{ink};line-height:1.25;margin-top:1px;">{_esc(rec["title"])}</div>'
            f'{links}</div>')

    # header + all-day band + grid body, per column
    has_allday = any(by_day[c]["allday"] for c in cols)
    heads, bands, bodies = [], [], []
    for c in cols:
        wknd = c.weekday() >= 5
        is_today = c == today
        dow = DOW[c.weekday()]
        head_top = f"border-top:3px solid {TODAY_TOP};" if is_today else ""
        dcol = FOREST if (is_today or not wknd) else GUTTER
        ncol = FOREST if is_today else (INK if not wknd else GUTTER)
        cnt = len(by_day[c]["timed"]) + len(by_day[c]["allday"])
        chip = (f'<span style="display:inline-block;margin-left:5px;padding:1px 6px;'
                f'font-size:10px;font-weight:bold;color:{FOREST};background:{WIN_FILL};'
                f'border:1px solid {MOSS};border-radius:2px;">{cnt}</span>' if cnt else "")
        tag = " · Today" if is_today else ""
        heads.append(
            f'<td style="width:{COLW}px;{head_top}border-bottom:2px solid {HAIR_STRONG};'
            f'border-left:1px solid {HAIRLINE};padding:8px 8px 7px;vertical-align:top;">'
            f'<span style="display:block;font-size:10px;font-weight:bold;'
            f'text-transform:uppercase;letter-spacing:0.1em;color:{dcol};">{dow}{tag}</span>'
            f'<span style="font-size:19px;color:{ncol};">{c.day}</span>{chip}</td>')

        if has_allday:
            ad = "".join(
                f'<div style="background:{PERS_FILL if e["kind"]=="personal" else WIN_FILL};'
                f'border-left:3px solid {PERS_BORDER if e["kind"]=="personal" else WIN_BORDER};'
                f'border-radius:2px;padding:2px 5px;margin:2px 3px;font-size:10px;'
                f'color:{PERS_INK if e["kind"]=="personal" else WIN_INK};overflow:hidden;'
                f'white-space:nowrap;text-overflow:ellipsis;">{_esc(e["title"])}</div>'
                for e in by_day[c]["allday"])
            bands.append(
                f'<td style="border-left:1px solid {HAIRLINE};border-bottom:1px solid {HAIR_STRONG};'
                f'background:{OFF_FILL if wknd else "#FFFFFF"};vertical-align:top;'
                f'min-height:22px;padding:1px 0;">{ad or "&nbsp;"}</td>')

        rules = "".join(
            f'<div style="position:absolute;left:0;right:0;top:{int((hh*60-gmin)*PXMIN)}px;'
            f'height:0;border-top:1px solid {HAIRLINE};"></div>' for hh in hours)
        blocks = "".join(block(e, lane, n) for e, lane, n in _lanes(by_day[c]["timed"]))
        bodies.append(
            f'<td style="width:{COLW}px;border-left:1px solid {HAIRLINE};padding:0;vertical-align:top;">'
            f'<div style="position:relative;height:{grid_h}px;'
            f'background:{OFF_FILL if wknd else "#FFFFFF"};">{rules}{blocks}</div></td>')

    # time gutter
    gutter_rules = "".join(
        f'<div style="position:absolute;right:6px;top:{int((hh*60-gmin)*PXMIN)-6}px;'
        f'font-size:10px;font-weight:bold;letter-spacing:0.06em;text-transform:uppercase;'
        f'color:{GUTTER};">{((hh-1)%12)+1} {"AM" if hh<12 else "PM"}</div>' for hh in hours)
    gutter_head = (f'<td style="border-bottom:2px solid {HAIR_STRONG};padding:8px 4px 7px;'
                   f'width:46px;">&nbsp;</td>')
    gutter_band = (f'<td style="border-bottom:1px solid {HAIR_STRONG};">&nbsp;</td>'
                   if has_allday else "")
    gutter_body = (f'<td style="width:46px;padding:0;vertical-align:top;">'
                   f'<div style="position:relative;height:{grid_h}px;">{gutter_rules}</div></td>')

    band_row = (f'<tr>{gutter_band}{"".join(bands)}</tr>' if has_allday else "")
    allday_note = ('<span style="color:%s;font-size:10px;"> · all-day events banded at top</span>' % SUB
                   if has_allday else "")

    span = f"{cols[0].strftime('%B %-d')} – {cols[-1].strftime('%B %-d, %Y')}"
    vlabel = "Sun–Sat week" if view == "week" else "Next 7 days"

    # Print rules live in a <style> block rather than inline, because @page and
    # @media have no inline equivalent. Without these, ⌘P gives a clipped,
    # colourless page: the grid sits in an overflow-x scroller (cut off at the
    # paper edge) and browsers drop background colours by default, which is the
    # entire visual language of the blocks.
    #
    # One page, always. The grid is as tall as the day is long (1px/minute), so
    # a real week overflows landscape Letter and splits — and `break-inside:
    # avoid` is ignored once content exceeds a page, so the split lands
    # mid-event. Nothing in CSS can shrink-to-fit, but we know the exact height
    # here, so scale the whole sheet by the ratio that makes it fit. `zoom`
    # (not `transform`) because it reflows rather than leaving a hole.
    # Constants measured, not estimated: binary-searching the largest zoom that
    # still prints one page put the non-grid chrome at 237px with an all-day
    # band. SAFETY covers font-metric drift between browsers — Safari lays the
    # header out a few px taller than Chrome, and being 1% too big costs a whole
    # second page while being 3% too small is invisible.
    PAGE_H = 748          # 8.5in landscape - 2*0.35in margin, at 96dpi
    PAGE_W = 988          # 11in - 2*0.35in
    SAFETY = 0.97
    chrome_h = 215 + (35 if has_allday else 0)   # title, column heads, legend, footer
    content_h = grid_h + chrome_h
    content_w = 46 + COLW * len(cols) + 8
    fit = min(1.0, (PAGE_H / content_h) * SAFETY, (PAGE_W / content_w) * SAFETY)
    zoom = f"\n    .cpWrap {{ zoom: {fit:.3f}; }}   /* shrink-to-one-page */" if fit < 1 else ""
    print_css = f"""
  @page {{ size: landscape; margin: 0.35in; }}
  @media print {{
    html, body {{ background: #FFFFFF !important; }}
    /* keep the fills/borders — they carry work-vs-personal and the today marker */
    * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
    .cpWrap {{ max-width: none !important; padding: 0 !important; }}
    .cpScroll {{ overflow: visible !important; }}      /* else the week is cut at the margin */
    .cpScroll table {{ page-break-inside: avoid; break-inside: avoid; }}
    .cpFoot {{ page-break-before: avoid; break-before: avoid; }}{zoom}
  }}"""

    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Weekly Calendar — {span}</title>
<style>{print_css}
</style></head>
<body style="margin:0;background:#FFFFFF;">
<div class="cpWrap" style="max-width:1100px;margin:0 auto;padding:28px 22px 40px;font-family:Arial,'Helvetica Neue',Helvetica,sans-serif;color:{INK};">
  <p style="margin:0 0 6px;font-size:11px;font-weight:bold;text-transform:uppercase;letter-spacing:0.14em;color:{OLIVE};">RJS Research LLC</p>
  <h1 style="margin:0 0 4px;font-family:Georgia,'Times New Roman',serif;font-size:24px;font-weight:bold;color:{FOREST};">Weekly Calendar</h1>
  <p style="margin:0 0 16px;font-size:13px;color:{SUB};"><strong style="color:{INK};">{span}</strong> &nbsp;·&nbsp; {vlabel}{allday_note}</p>
  <div class="cpScroll" style="overflow-x:auto;">
    <table style="border-collapse:collapse;table-layout:fixed;" cellpadding="0" cellspacing="0">
      <tr>{gutter_head}{"".join(heads)}</tr>
      {band_row}
      <tr>{gutter_body}{"".join(bodies)}</tr>
    </table>
  </div>
  <p style="margin:18px 0 0;font-size:11px;color:{SUB};">
    <span style="display:inline-block;width:11px;height:11px;background:{WIN_FILL};border-left:3px solid {WIN_BORDER};vertical-align:middle;"></span> Work
    &nbsp;&nbsp;
    <span style="display:inline-block;width:11px;height:11px;background:{PERS_FILL};border-left:3px solid {PERS_BORDER};vertical-align:middle;"></span> Personal
  </p>
  <p class="cpFoot" style="margin:10px 0 0;padding-top:12px;border-top:1px solid {HAIRLINE};font-size:11px;color:{SUB};">Prepared by RJS Research LLC.</p>
</div>
</body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser(description="render deduped events to HTML")
    ap.add_argument("--view", default="week", choices=["week", "rolling"])
    ap.add_argument("--ref", default=None, help="reference date YYYY-MM-DD (default: today)")
    ap.add_argument("--out", default=None, help="output HTML path (default: stdout)")
    a = ap.parse_args()
    payload = json.load(sys.stdin)
    events = payload["events"] if isinstance(payload, dict) else payload
    ref = date.fromisoformat(a.ref) if a.ref else date.today()
    html = render(events, a.view, ref)
    if a.out:
        with open(a.out, "w") as f:
            f.write(html)
        print(f"wrote {a.out} ({a.view}, ref={ref})")
    else:
        sys.stdout.write(html)


if __name__ == "__main__":
    main()
