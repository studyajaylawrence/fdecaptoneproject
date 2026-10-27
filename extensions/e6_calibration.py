#!/usr/bin/env python3
"""Extension E6 - check whether "High" means high.

Author: Ajay Lawrence - implementation of extension E6 (see extensions/README.md).

Builds the calibration table from an evaluation results file: for answers labelled High,
Moderate and Low, what share actually passed their checks. Lists the disagreements worth
reading - a High that failed (dangerous: step 3 may release it) and a Low that passed (cheap:
it costs a clinician review). Exits 1 if any High-confidence answer failed.

    python extensions/e6_calibration.py
    python extensions/e6_calibration.py --results extensions/results/e5-mini.jsonl

Also reports the share of answers that would reach a human anyway: an agent that labels
everything Moderate is perfectly calibrated and saves nobody any time.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

# Offline analysis only: no Azure or .env needed, so ext_common is not imported.
EXT = pathlib.Path(__file__).resolve().parent
ROOT = EXT.parent

LABELS = ("High", "Moderate", "Low")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", type=pathlib.Path, default=ROOT / "results.jsonl")
    args = parser.parse_args()
    rows = [json.loads(l) for l in args.results.read_text(encoding="utf-8").splitlines() if l.strip()]

    lines = [f"# E6 - confidence calibration ({args.results.name})", "",
             "| Label | Answers | Passed checks | Share correct |", "|---|---|---|---|"]
    for label in LABELS:
        group = [r for r in rows if r["confidence"] == label]
        passed = sum(r["passed"] for r in group)
        share = f"{passed / len(group):.0%}" if group else "-"
        lines.append(f"| {label} | {len(group)} | {passed} | {share} |")

    high_fail = [r for r in rows if r["confidence"] == "High" and not r["passed"]]
    low_pass = [r for r in rows if r["confidence"] == "Low" and r["passed"] and r["category"] == "answerable"]
    reviewed = sum(1 for r in rows if r["requires_clinician_review"] or r["confidence"] != "High")
    lines += ["", f"High-confidence failures: **{len(high_fail)}** (target 0)"]
    for r in high_fail:
        failed = [k for k, v in r["checks"].items() if not v]
        lines.append(f"- {r['id']} ({r['category']}) failed {failed}: {' '.join(r['answer'].split())[:160]}")
    lines += ["", f"Low-confidence answers that were correct: {len(low_pass)}"]
    lines += [f"- {r['id']}: {r['query'][:100]}" for r in low_pass]
    lines += ["", f"Usefulness: {len(rows) - reviewed}/{len(rows)} answers are High and not flagged "
                  f"for review, i.e. could be released without a clinician.", "",
              "## What changed and why", "", "_One sentence on the rule you tightened and the class of error it fixed._", ""]

    out = EXT / "results" / "e6-calibration.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"written to {out}")
    return 1 if high_fail else 0


if __name__ == "__main__":
    sys.exit(main())
