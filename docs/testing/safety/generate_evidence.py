"""Run the safety API tests and turn the real run into evidence files.

Responsibilities:
    - Run ``test_safety_api.py`` and ``test_prediction_result_api.py`` with
      ``-v`` and save the full terminal output to ``pytest-output.txt``.
    - While the tests run, record every assessment each test sent through the
      API (input symptoms and the actual result), using this file as a pytest
      plugin. Nothing is typed in by hand: every card shows captured data.
    - Draw ``screenshots/terminal-run.png`` and one ``TC-SAF-A-xx.png`` card
      per test case.

Usage (from the repository root, with the server virtualenv):
    server/.venv/bin/python docs/testing/safety/generate_evidence.py

Owner: Nisarg · Task: S2-NIS-23 · Issue: #330
TC-SAF-A-17 passes after the #348 fix: Nisarg · S2-NIS-28 (#348)
Records card edits for TC-SAF-A-21/22: Nisarg · S2-NIS-29 (#351)
Requirements: DR-01, DR-02, FR-05, FR-06, FR-08, FR-22, FR-23
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SERVER = REPO / "server"
SHOTS = HERE / "screenshots"
RECORD_FILE = HERE / ".evidence-runs.json"
TEST_FILES = [
    "tests/integration/test_safety_api.py",
    "tests/integration/test_prediction_result_api.py",
]
# ---------------------------------------------------------------------------
# pytest plugin part: records each run_assessment() call per test case
# ---------------------------------------------------------------------------

_RUNS: dict[str, list[dict[str, Any]]] = {}
_OUTCOMES: dict[str, dict[str, Any]] = {}
_CURRENT: dict[str, str] = {"tc": ""}


def _tc_id(nodeid: str) -> str:
    """``...::test_tc_saf_a_07_...`` -> ``TC-SAF-A-07``."""
    match = re.search(r"test_tc_saf_a_(\d+)", nodeid)
    return f"TC-SAF-A-{match.group(1)}" if match else nodeid


def pytest_configure(config: Any) -> None:
    """Wrap the shared helper so every API run is recorded."""
    from tests.integration import safety_support

    original = safety_support.run_assessment

    async def recording_run(client, symptoms, headers=None):  # type: ignore[no-untyped-def]
        run = await original(client, symptoms, headers)
        _RUNS.setdefault(_CURRENT["tc"], []).append(
            {
                "symptoms": [list(s) for s in symptoms],
                "signedIn": bool(headers),
                "analyzeStatus": run.analyze_status,
                "analyzeBody": run.bodies[-2],
                "resultStatus": run.result_status,
                "result": run.result,
            }
        )
        return run

    safety_support.run_assessment = recording_run

    original_edit = safety_support.run_card_edit

    async def recording_edit(client, message, keep, add=()):  # type: ignore[no-untyped-def]
        run = await original_edit(client, message, keep, add)
        _RUNS.setdefault(_CURRENT["tc"], []).append(
            {
                "message": message,
                "extracted": run.extracted,
                "confirmed": run.confirmed,
                "symptoms": [list(s) for s in add],
                "signedIn": False,
                "analyzeStatus": run.analyze_status,
                "analyzeBody": run.bodies[-2],
                "resultStatus": run.result_status,
                "result": run.result,
            }
        )
        return run

    safety_support.run_card_edit = recording_edit


def pytest_runtest_setup(item: Any) -> None:
    """Remember which test case is running."""
    _CURRENT["tc"] = _tc_id(item.nodeid)


def pytest_runtest_logreport(report: Any) -> None:
    """Keep each test case's outcome and duration."""
    if report.when == "call" or (report.when == "setup" and report.failed):
        outcome = report.outcome
        if hasattr(report, "wasxfail"):
            outcome = "xfailed"
        _OUTCOMES[_tc_id(report.nodeid)] = {
            "outcome": outcome,
            "duration": round(report.duration, 3),
            "longrepr": str(report.longrepr) if report.failed else "",
        }


def pytest_sessionfinish(session: Any) -> None:
    """Write what was recorded for the drawing step."""
    target = Path(os.environ.get("SAFETY_EVIDENCE_OUT", RECORD_FILE))
    target.write_text(
        json.dumps({"runs": _RUNS, "outcomes": _OUTCOMES}, indent=1),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

BG = (24, 26, 32)
PANEL = (34, 37, 46)
FG = (220, 223, 228)
DIM = (140, 146, 158)
GREEN = (126, 211, 133)
RED = (240, 113, 120)
AMBER = (240, 190, 100)
BLUE = (110, 170, 245)


def _font(size: int, bold: bool = False) -> Any:
    """Menlo on macOS, DejaVu Sans Mono on Linux, Pillow's default otherwise."""
    from PIL import ImageFont

    candidates = [
        ("/System/Library/Fonts/Menlo.ttc", 1 if bold else 0),
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono"
            + ("-Bold" if bold else "")
            + ".ttf",
            0,
        ),
        ("consolab.ttf" if bold else "consola.ttf", 0),
    ]
    for path, index in candidates:
        try:
            return ImageFont.truetype(path, size, index=index)
        except OSError:
            continue
    return ImageFont.load_default()


def _save(image: Any, name: str) -> None:
    """Save as an optimised PNG (each file stays well under 1 MB)."""
    SHOTS.mkdir(parents=True, exist_ok=True)
    path = SHOTS / name
    image.save(path, optimize=True)
    assert path.stat().st_size < 1_000_000, path


def draw_terminal(lines: list[str], name: str, title: str) -> None:
    """Draw terminal text as a dark terminal window."""
    from PIL import Image, ImageDraw

    font = _font(13)
    bold = _font(13, bold=True)
    line_h = 18
    width = 1500
    height = 44 + line_h * len(lines) + 20
    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, width, 30], fill=PANEL)
    for i, colour in enumerate((RED, AMBER, GREEN)):
        draw.ellipse([12 + i * 20, 9, 24 + i * 20, 21], fill=colour)
    draw.text((80, 7), title, font=bold, fill=DIM)
    y = 40
    for line in lines:
        colour = FG
        if " PASSED" in line or re.search(r"\d+ passed", line):
            colour = GREEN
        if " XFAIL" in line or "xfailed" in line:
            colour = AMBER
        if " FAILED" in line or line.startswith("E "):
            colour = RED
        if line.startswith("$"):
            colour = BLUE
        draw.text((14, y), line[:200], font=font, fill=colour)
        y += line_h
    _save(image, name)


def _summarise(run: dict[str, Any]) -> list[str]:
    """Plain-text lines describing one captured run."""
    symptoms = ", ".join(f"{n} ({s.lower()})" for n, s in run["symptoms"])
    if "message" in run:
        lines = [
            f'Chat: "{run["message"]}"',
            f"AI extracted: {run['extracted']}",
            f"Stored after the card's PATCH /symptoms: {run['confirmed']}",
        ]
    else:
        lines = [
            f"Input: {symptoms}" + ("   [signed-in user]" if run["signedIn"] else "")
        ]
    result = run["result"]
    if run["resultStatus"] != 200:
        analyze = json.loads(run["analyzeBody"])
        lines.append(
            f"POST /analyze -> HTTP {run['analyzeStatus']} {analyze.get('code', '')}: "
            f"{analyze.get('message', '')}"
        )
        lines.append(
            f"GET /result   -> HTTP {run['resultStatus']} {result.get('code', '')}: "
            f"{result.get('message', '')}"
        )
        return lines
    referral = result["referral"]
    lines.append(
        f"riskLevel={result['riskLevel']}  referral.specialty={referral['specialty']}"
        f"  emergencyNumber={referral['emergencyNumber']}"
    )
    for c in result["conditions"]:
        lines.append(
            f"  #{c['rank']} {c['name']} [{c['confidence']}] -> {c['specialty']}"
        )
        lines.append(f"     why: {c['why']}")
    if not result["conditions"]:
        lines.append("  conditions: [] (none matched)")
    lines.append(f"  guidance[0]: {result['guidance'][0]}")
    if referral["reason"]:
        lines.append(f"  referral.reason: {referral['reason']}")
    lines.append(f"  disclaimer: {result['disclaimer']}")
    return lines


def draw_card(case: dict[str, str], outcome: dict[str, Any], runs: list[dict]) -> None:
    """One evidence card: what was tested, the outcome, the captured output."""
    from PIL import Image, ImageDraw

    title_font = _font(17, bold=True)
    font = _font(13)
    bold = _font(13, bold=True)
    width = 1300

    status = {"passed": "PASS", "xfailed": "FAIL (expected)"}.get(
        outcome["outcome"], outcome["outcome"].upper()
    )
    status_colour = GREEN if status == "PASS" else RED

    body: list[tuple[str, tuple[int, int, int], Any]] = []

    def add(text: str, colour: tuple[int, int, int] = FG, f: Any = font) -> None:
        for chunk in textwrap.wrap(text, 150, subsequent_indent="       ") or [""]:
            body.append((chunk, colour, f))

    add(f"Requirement: {case['req']}    Technique: {case['technique']}", DIM)
    add(f"Expected: {case['expected']}", BLUE)
    add("")
    add("ACTUAL (captured from the API during this test run):", AMBER, bold)
    shown = runs[: case.get("max_runs", 4)]
    for run in shown:
        for line in _summarise(run):
            add(line)
        add("")
    if len(runs) > len(shown):
        add(f"... {len(runs) - len(shown)} more runs in this test, all asserted.", DIM)
    if case.get("extra"):
        add(case["extra"], AMBER)
    add(
        f"pytest: {outcome['outcome'].upper()} in {outcome['duration']} s"
        "   (AI_PROVIDER=mock, isolated SQLite database)",
        DIM,
    )

    line_h = 18
    height = 70 + line_h * len(body) + 40
    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, width, 50], fill=PANEL)
    draw.text((16, 15), f"[{case['id']}] {case['title']}", font=title_font, fill=BLUE)
    draw.text(
        (width - 16 - draw.textlength(status, font=title_font), 15),
        status,
        font=title_font,
        fill=status_colour,
    )
    y = 64
    for text, colour, f in body:
        draw.text((16, y), text, font=f, fill=colour)
        y += line_h
    draw.text(
        (16, height - 26),
        "AI-Based Symptom Checker · S2-NIS-23 (#330) safety & prediction API tests"
        " · Tester: Nisarg",
        font=font,
        fill=DIM,
    )
    _save(image, f"{case['id']}.png")


#: Title, requirement, technique and expected result per test case. These
#: match the rows in test-cases.md; the actual values come from the run.
CASES: list[dict[str, Any]] = [
    {"id": "TC-SAF-A-01", "title": "Chest pain + breathlessness -> URGENT, 112",
     "req": "DR-02, FR-06", "technique": "Decision table",
     "expected": "URGENT, emergencyNumber 112, Emergency department, even though "
     "no condition is Likely"},
    {"id": "TC-SAF-A-02", "title": "Stroke sign (face drooping) -> URGENT",
     "req": "DR-02, FR-06", "technique": "Decision table",
     "expected": "URGENT with 112; one stroke sign is enough"},
    {"id": "TC-SAF-A-03", "title": "Vomiting blood -> URGENT with no condition",
     "req": "DR-02, FR-06", "technique": "Decision table",
     "expected": "URGENT with 112 although the condition list is empty"},
    {"id": "TC-SAF-A-04", "title": "Fever + stiff neck -> URGENT; fever alone not",
     "req": "DR-02, FR-06", "technique": "Decision table (combined condition)",
     "expected": "fever + stiff neck = URGENT; fever alone is not URGENT"},
    {"id": "TC-SAF-A-05", "title": "Thoughts of self-harm -> URGENT + helpline",
     "req": "DR-02, FR-06", "technique": "Decision table",
     "expected": "URGENT, 112, and the Tele-MANAS 14416 helpline step"},
    {"id": "TC-SAF-A-06", "title": "Chest pain alone: severity boundary",
     "req": "DR-02, FR-06", "technique": "BVA",
     "expected": "MILD and MODERATE = CONSULT_DOCTOR (no 112); SEVERE = URGENT"},
    {"id": "TC-SAF-A-07", "title": "Unstated severity never lowers risk",
     "req": "DR-02, FR-06", "technique": "Error guessing",
     "expected": "chest pain, UNKNOWN severity = URGENT + 'treated as urgent' note"},
    {"id": "TC-SAF-A-08", "title": "Mild cold symptoms -> SELF_CARE",
     "req": "FR-06", "technique": "Decision table",
     "expected": "SELF_CARE, referral not required, no emergency number"},
    {"id": "TC-SAF-A-09", "title": "Low confidence raises SELF_CARE",
     "req": "FR-06, DR-02", "technique": "Decision table",
     "expected": "no Likely condition -> CONSULT_DOCTOR + 'raised to the safer level'"},
    {"id": "TC-SAF-A-10", "title": "Low confidence never lowers a tier",
     "req": "FR-06, DR-02", "technique": "Decision table",
     "expected": "no Likely condition, URGENT stays URGENT, CONSULT stays CONSULT"},
    {"id": "TC-SAF-A-11", "title": "Disclaimer on every tier; no percentages",
     "req": "DR-01, FR-22", "technique": "EP (one run per tier) + regex scan",
     "expected": "disclaimer on all 3 tiers; no '%', 'probability', 'score' or "
     "decimal number in any response of the flow",
     "max_runs": 3,
     "extra": "Scanned: all 6 responses per run (create, chat, 2x symptoms, "
     "analyze, result) for /\\d+%/ and /probabilit|percent|score/: 0 matches."},
    {"id": "TC-SAF-A-12", "title": "Confidence labels: only 3 partitions",
     "req": "FR-22", "technique": "EP",
     "expected": "every label in {LIKELY, POSSIBLE, LESS_LIKELY}; all 3 seen",
     "max_runs": 2},
    {"id": "TC-SAF-A-13", "title": "Ranked 1..n with why + specialty",
     "req": "FR-05, FR-23", "technique": "EP",
     "expected": "ranks 1,2,3 in order (max 3); each has 'Because you reported...' "
     "and a specialty", "max_runs": 2},
    {"id": "TC-SAF-A-14", "title": "One symptom (lower boundary)",
     "req": "FR-05", "technique": "BVA",
     "expected": "complete result, rank 1 condition, why names the symptom"},
    {"id": "TC-SAF-A-15", "title": "Twelve symptoms (upper boundary)",
     "req": "FR-05, FR-23", "technique": "BVA",
     "expected": "at most 3 conditions; why line shortened ('and N other symptoms')"},
    {"id": "TC-SAF-A-16", "title": "Unknown + known symptoms -> safe fallback",
     "req": "FR-05, FR-07", "technique": "Error guessing",
     "expected": "unknown symptoms ignored; CONSULT_DOCTOR, General physician"},
    {"id": "TC-SAF-A-17", "title": "Only unknown symptoms -> General physician",
     "req": "FR-05, FR-06, idea §7", "technique": "BVA / Error guessing",
     "expected": "CONSULT_DOCTOR with a General physician referral; state COMPLETED",
     "extra": "Found defect #348 (before the fix: analyze 422, stuck in ANALYZING;"
     " see TC-SAF-A-17-failure.png). Fixed in S2-NIS-28; passes now."},
    {"id": "TC-SAF-A-18", "title": "Repeatability: same input 3x = same output",
     "req": "FR-05, FR-06", "technique": "Repeatability (deterministic model)",
     "expected": "identical tier, conditions, guidance, referral in all 3 runs",
     "max_runs": 3,
     "extra": "9 runs in total: 3 inputs x 3 runs each; all 3 runs per input "
     "compared field by field and found identical."},
    {"id": "TC-SAF-A-19", "title": "Referral: specialty for map search, no PII",
     "req": "FR-08, DR-04", "technique": "Error guessing",
     "expected": "specialty 'General physician' -> query 'General physician near "
     "me'; only published keys; no email, user ID, consent ID or doctor data",
     "extra": "Map query built like DoctorReferral.tsx: 'General physician near me'."
     " Result keys = 9 published keys only; email/user ID/consent ID: 0 matches."},
    {"id": "TC-SAF-A-20", "title": "Guidance matches the risk tier",
     "req": "FR-06, DR-02", "technique": "EP (one run per tier)",
     "expected": "SELF_CARE: home care steps; CONSULT: 'Book a visit'; "
     "URGENT: 'Call 112 now', no home-care step", "max_runs": 3},
    {"id": "TC-SAF-A-21", "title": "Removed red flag no longer counts (#351)",
     "req": "FR-16, DR-02", "technique": "Error guessing / regression",
     "expected": "card keeps only headache -> stored list = [headache]; result "
     "not URGENT; no 'chest pain' in any why line",
     "extra": "Before the #351 fix the stored list stayed [chest_pain, headache] "
     "and the result was URGENT."},
    {"id": "TC-SAF-A-22", "title": "Card edit replaces the list (#351)",
     "req": "FR-03, FR-16", "technique": "State / regression",
     "expected": "remove headache + add fever -> only fever; empty list -> "
     "stored [] and analyze refused (400)",
     "extra": "Before the #351 fix the stored list stayed [headache, fever]."},
]


def _clean_output(text: str) -> str:
    """Drop the local home-directory prefix from paths in the output."""
    return text.replace(str(REPO) + "/", "").replace(str(Path.home()), "~")


def main() -> int:
    """Run the tests, then draw the terminal and per-test-case screenshots."""
    env = {
        **os.environ,
        "PYTHONPATH": f"{HERE}{os.pathsep}{SERVER}",
        "AI_PROVIDER": "mock",
        "CV_PROVIDER": "mock",
        "SAFETY_EVIDENCE_OUT": str(RECORD_FILE),
    }
    command = [sys.executable, "-m", "pytest", *TEST_FILES, "-v",
               "-p", "generate_evidence", "-p", "no:cacheprovider"]
    proc = subprocess.run(command, cwd=SERVER, env=env, capture_output=True,
                          text=True, check=False)
    output = _clean_output(proc.stdout + proc.stderr)
    shown_cmd = "$ cd server && python -m pytest " + " ".join(TEST_FILES) + " -v"
    (HERE / "pytest-output.txt").write_text(shown_cmd + "\n" + output,
                                            encoding="utf-8")
    recorded = json.loads(RECORD_FILE.read_text(encoding="utf-8"))
    RECORD_FILE.unlink()

    # Terminal screenshot: header, every test line and the summary.
    lines = output.splitlines()
    keep = [shown_cmd]
    for line in lines:
        if line.startswith(("platform", "rootdir", "configfile", "plugins",
                            "collected", "=====", "tests/integration", "XFAIL")):
            if "warnings summary" in line:
                continue
            if line.startswith("tests/integration") and not re.search(
                r" (PASSED|XFAIL|FAILED|ERROR)", line
            ):
                continue
            keep.append(line)
    draw_terminal(keep, "terminal-run.png", "Terminal: S2-NIS-23 safety API tests")

    for case in CASES:
        outcome = recorded["outcomes"].get(case["id"])
        assert outcome, f"no outcome recorded for {case['id']}"
        draw_card(case, outcome, recorded["runs"].get(case["id"], []))

    print(output.splitlines()[-1])
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
