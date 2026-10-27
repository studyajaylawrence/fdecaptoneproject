#!/usr/bin/env python3
"""Extension E2 - compare per-setting results files produced by the manual scenario.

    python extensions/e2_compare.py --planning minimal=0 low=1 medium=2 `
        --elapsed minimal=310 low=420 medium=560

Reads extensions/results/e2-<level>.jsonl for each level and prints:
  1. a summary table (checks passed, planning passes, elapsed, agent tokens)
  2. per-question differences: pass/fail, failed checks, confidence, citations, token use
Then writes the same report to extensions/results/e2-retrieval-effort.md.
"""
from __future__ import annotations

import argparse
import json
import pathlib

RESULTS = pathlib.Path(__file__).resolve().parent / "results"
LEVELS = ["minimal", "low", "medium"]


def _kv(pairs: list[str]) -> dict[str, str]:
    return dict(p.split("=", 1) for p in pairs or [])


def _load(level: str) -> list[dict]:
    path = RESULTS / f"e2-{level}.jsonl"
    if not path.exists():
        raise SystemExit(f"missing {path} - run the evaluation for '{level}' first")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _tok(rows: list[dict], key: str) -> int:
    return sum((r.get("_telemetry") or {}).get(key) or 0 for r in rows)


def _cited(row: dict) -> str:
    return ", ".join(sorted({c["document"].split(" ")[0] for c in row.get("citations", [])})) or "-"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--levels", nargs="+", default=LEVELS, choices=LEVELS)
    parser.add_argument("--planning", nargs="*", help="level=passes from step1 --test")
    parser.add_argument("--elapsed", nargs="*", help="level=seconds of wall-clock evaluation time")
    args = parser.parse_args()
    planning, elapsed = _kv(args.planning), _kv(args.elapsed)

    data = {level: {r["id"]: r for r in _load(level)} for level in args.levels}

    lines = ["# E2 - retrieval effort comparison", "",
             "| Effort | Output mode | Checks passed | Planning passes | Elapsed (s) | Input tokens | Output tokens |",
             "|---|---|---|---|---|---|---|"]
    for level in args.levels:
        rows = list(data[level].values())
        mode = "extractiveData" if level == "minimal" else "answerSynthesis"
        lines.append(f"| {level} | {mode} | {sum(r['passed'] for r in rows)}/{len(rows)} | "
                     f"{planning.get(level, '?')} | {elapsed.get(level, '?')} | "
                     f"{_tok(rows, 'input_tokens'):,} | {_tok(rows, 'output_tokens'):,} |")

    # Per-question quality differences - more informative than totals.
    ids = sorted(set.intersection(*(set(d) for d in data.values())))
    lines += ["", "## Questions whose answer quality changed", "",
              "| Question | " + " | ".join(args.levels) + " |",
              "|---" * (len(args.levels) + 1) + "|"]
    changed = 0
    for qid in ids:
        rows = [data[level][qid] for level in args.levels]
        signature = {(r["passed"], r["confidence"], _cited(r), r["requires_clinician_review"]) for r in rows}
        if len(signature) == 1:
            continue
        changed += 1
        cells = []
        for r in rows:
            failed = [k for k, v in r["checks"].items() if not v]
            verdict = "pass" if r["passed"] else "FAIL: " + ",".join(failed)
            cells.append(f"{verdict}<br>{r['confidence']} · {_cited(r)}"
                         f"{' · review' if r['requires_clinician_review'] else ''}")
        lines.append(f"| {qid} {rows[0]['query'][:60]} | " + " | ".join(cells) + " |")
    if not changed:
        lines.append("| none | " + " | ".join("same" for _ in args.levels) + " |")

    lines += ["", "## Recommendation", "",
              "_Which setting would you ship, and what trade-off did you accept?_", ""]
    out = RESULTS / "e2-retrieval-effort.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
