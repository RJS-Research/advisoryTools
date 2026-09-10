#!/usr/bin/env python3
"""calPreview delivery doctor — capture install/runtime health into one report
that the end user hands back for improving the DELIVERY PATHWAY (not the
calendar features).

    python3 doctor.py                 # probe + write deliveryReport_<ts>.md
    python3 doctor.py --note "text"   # attach a freeform note
    python3 doctor.py --record-failure "step" "detail"   # called by build.py on a crash

It probes only the runtime steps a script can see (osascript, EventKit auth, a
real pull, the dedupe/render gate, the claude CLI). Delivery steps that happen
before any script runs (the emailed clone command, Xcode CLT popup, Claude
sign-in) are captured as LLM/user observations.

Every friction point is layer-tagged — code | llm-advised | llm — so we know
what to harden into pure code next (the progression goal).
"""
import argparse
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../skills/calPreview/scripts
SKILL_ROOT = HERE.parent                          # .../skills/calPreview


def _plugin_version() -> str:
    for up in [HERE, *HERE.parents]:
        pj = up / ".claude-plugin" / "plugin.json"
        if pj.exists():
            try:
                return json.loads(pj.read_text()).get("version", "?")
            except Exception:  # noqa: BLE001
                return "?"
    return "?"


def _run(cmd, timeout=60):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError as e:
        return 127, "", f"not found: {e}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timed out after {timeout}s"
    except Exception as e:  # noqa: BLE001
        return 1, "", repr(e)


def probe_env() -> dict:
    return {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "toolVersion": _plugin_version(),
        "os": f"{platform.system()} {platform.mac_ver()[0] or platform.release()}",
        "arch": platform.machine(),
        "python": platform.python_version(),
        "osascript": bool(shutil.which("osascript")),
        "claudeCli": bool(shutil.which("claude")),
    }


def probe_steps() -> list:
    """Each step: {step, result: ok|fail|blocked|warn, detail}."""
    steps = []

    # 1. osascript reachable at all (a sandbox may block spawning it)
    if not shutil.which("osascript"):
        steps.append({"step": "osascript reachable", "result": "blocked",
                      "detail": "osascript not on PATH — cannot pull local calendar",
                      "layer": "code"})
        return steps
    rc, out, errtxt = _run(["osascript", "-l", "JavaScript", "-e",
                            'ObjC.import("EventKit"); "ok"'], timeout=20)
    if rc != 0:
        steps.append({"step": "osascript reachable", "result": "blocked",
                      "detail": f"rc={rc}; {errtxt.strip()[:300]} "
                                "(host app may sandbox osascript — the go/no-go)",
                      "layer": "llm-advised"})
        return steps
    steps.append({"step": "osascript reachable", "result": "ok", "detail": "",
                  "layer": "code"})

    # 2. EventKit authorization status
    rc, out, errtxt = _run(["osascript", "-l", "JavaScript", "-e",
        'ObjC.import("EventKit"); '
        'String($.EKEventStore.authorizationStatusForEntityType($.EKEntityTypeEvent))'],
        timeout=20)
    st = (out or "").strip()
    label = {"0": "notDetermined", "2": "denied/restricted", "3": "fullAccess",
             "4": "writeOnly"}.get(st, f"raw={st!r}")
    steps.append({"step": "EventKit auth status",
                  "result": "ok" if st == "3" else ("warn" if st == "0" else "fail"),
                  "detail": f"{st} ({label})", "layer": "code"})

    # 3. a real pull over a 3-day window around today
    pull = HERE / "pull.js"
    today = datetime.now().date()
    rc, out, errtxt = _run(["osascript", "-l", "JavaScript", str(pull),
                            (today - timedelta(days=1)).isoformat(),
                            (today + timedelta(days=2)).isoformat()], timeout=60)
    if rc == 0:
        try:
            n = len(json.loads(out))
            steps.append({"step": "calendar pull", "result": "ok",
                          "detail": f"{n} raw events in a 3-day window", "layer": "code"})
        except Exception as e:  # noqa: BLE001
            steps.append({"step": "calendar pull", "result": "fail",
                          "detail": f"pull ran but output not JSON: {e!r}", "layer": "code"})
    else:
        steps.append({"step": "calendar pull", "result": "fail" if rc == 2 else "blocked",
                      "detail": f"rc={rc}; {errtxt.strip()[:300]}", "layer": "llm-advised"})

    # 4. deterministic dedupe/render gate
    rc, out, errtxt = _run([sys.executable, str(HERE / "selfTest.py")], timeout=60)
    steps.append({"step": "dedupe/render gate",
                  "result": "ok" if rc == 0 else "fail",
                  "detail": "GATE PASSED" if rc == 0 else (errtxt or out).strip()[-300:],
                  "layer": "code"})
    return steps


def verdict(steps: list) -> str:
    if any(s["result"] == "blocked" for s in steps):
        return "BLOCKED"
    if any(s["result"] == "fail" for s in steps):
        return "PARTIAL"
    if any(s["result"] == "warn" for s in steps):
        return "NEEDS-PERMISSION"
    return "PASS"


def write_report(env, steps, notes, failures) -> Path:
    v = verdict(steps)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = SKILL_ROOT / f"deliveryReport_{ts}.md"
    rows = "\n".join(
        f"| {s['step']} | {s['result'].upper()} | {s.get('layer','')} | {s['detail']} |"
        for s in steps)
    notes_block = "\n".join(f"- {n}" for n in notes) or "_(none captured)_"
    fail_block = "\n".join(
        f"- **{f['step']}** — {f['detail']}" for f in failures) or "_(none)_"
    machine = json.dumps({"env": env, "steps": steps, "verdict": v,
                          "failures": failures, "notes": notes}, indent=2)
    out.write_text(f"""# calPreview — Delivery Report

**Verdict: {v}**  ·  generated {env['generatedAt']}  ·  tool v{env['toolVersion']}

> This report is about the **delivery/install pathway**, not the calendar
> features. Hand it back to improve how calPreview ships.

## Environment
- macOS: {env['os']}  ·  arch: {env['arch']}
- python3: {env['python']}  ·  osascript present: {env['osascript']}  ·  claude CLI present: {env['claudeCli']}

## Runtime probes
| Step | Result | Layer | Detail |
|---|---|---|---|
{rows}

*Layer key — `code` = deterministic (harden here last) · `llm-advised` = script
the LLM drives (harden next) · `llm` = pure model judgement (least stable).*

## Failures captured during use
{fail_block}

## Observations & improvements
_The assistant fills these while helping install. One entry per friction point:_

- **layer:** code | llm-advised | llm
  **severity:** blocker | major | minor | insight
  **what happened:**
  **suggested improvement (toward pure code where possible):**

{notes_block}

## Install steps not visible to this script
The emailed clone command, the Xcode command-line-tools popup, the Claude Code
installer, and Claude sign-in all happen before any script executes — record
friction there as observations above.

<!-- machine-readable -->
```json
{machine}
```
""")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="calPreview delivery doctor")
    ap.add_argument("--note", action="append", default=[],
                    help="freeform observation (repeatable)")
    ap.add_argument("--record-failure", nargs=2, metavar=("STEP", "DETAIL"),
                    action="append", default=[],
                    help="record a captured failure (used by build.py)")
    a = ap.parse_args()
    env = probe_env()
    steps = probe_steps()
    failures = [{"step": s, "detail": d} for s, d in a.record_failure]
    out = write_report(env, steps, a.note, failures)
    print(f"{verdict(steps)}  ->  {out}")


if __name__ == "__main__":
    main()
