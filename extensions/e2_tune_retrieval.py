#!/usr/bin/env python3
"""Extension E2 - measure retrieval effort instead of guessing.

Author: Ajay Lawrence - implementation of extension E2 (see extensions/README.md).

For each of minimal / low / medium: reconfigure your knowledge base, count query-planning passes
on the step 1 test question, run the full behaviour evaluation, and record pass rate, elapsed
time and agent tokens. Writes a table to extensions/results/e2-retrieval-effort.md plus one
results file per setting, then restores the knowledge base exactly as it was.

    python extensions/e2_tune_retrieval.py
    python extensions/e2_tune_retrieval.py --levels low medium

"minimal" cannot synthesize answers, so it runs with outputMode "extractiveData". That changes
what the agent receives as well as how retrieval plans - say so when you present the numbers.
"minimal" also rejects chat "messages" on /retrieve, so its test query is sent as a search
intent; with no query planning, its planning-pass count is always 0.
Token counts are the agent's own; the knowledge base's planning/synthesis calls are billed
separately and are not in `_telemetry` (see E5).
"""
from __future__ import annotations

import argparse
import copy

from ext_common import EXT, cfg

import lab_search as search
import step1_create_knowledge as step1
import step4_evaluate as step4

RESULTS_DIR = EXT / "results"


def _current_kb() -> dict:
    body = search.call("GET", f"/knowledgebases/{cfg.KB_NAME}")
    return {k: v for k, v in body.items() if not k.startswith("@")}


def _apply(base: dict, effort: str) -> None:
    body = copy.deepcopy(base)
    body["retrievalReasoningEffort"] = {"kind": effort}
    body["outputMode"] = "extractiveData" if effort == "minimal" else "answerSynthesis"
    search.call("PUT", f"/knowledgebases/{cfg.KB_NAME}", body)


def _tokens(rows: list[dict], key: str) -> int:
    return sum((r.get("_telemetry") or {}).get(key) or 0 for r in rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--levels", nargs="+", default=["minimal", "low", "medium"],
                        choices=["minimal", "low", "medium"])
    parser.add_argument("--name", default=cfg.AGENT_NAME)
    args = parser.parse_args()
    RESULTS_DIR.mkdir(exist_ok=True)

    original = _current_kb()
    summary: list[dict] = []
    per_question: dict[str, dict[str, bool]] = {}
    try:
        for level in args.levels:
            print(f"\n=== retrievalReasoningEffort = {level} ===")
            _apply(original, level)
            # minimal effort rejects "messages" input - it needs intents (and does no planning)
            planning = step1.test_retrieval(intents=level == "minimal")
            rows, elapsed = step4.evaluate(args.name, results=RESULTS_DIR / f"e2-{level}.jsonl")
            passed = sum(r["passed"] for r in rows)
            summary.append({"level": level, "passed": passed, "total": len(rows), "planning": planning,
                            "elapsed": elapsed, "in": _tokens(rows, "input_tokens"),
                            "out": _tokens(rows, "output_tokens")})
            for row in rows:
                per_question.setdefault(row["id"], {})[level] = row["passed"]
    finally:
        search.call("PUT", f"/knowledgebases/{cfg.KB_NAME}", original)
        print(f"\nrestored {cfg.KB_NAME} to its previous configuration")

    lines = ["# E2 - retrieval effort comparison", "",
             f"Agent `{args.name}`, knowledge base `{cfg.KB_NAME}`.", "",
             "| Effort | Output mode | Behaviour checks | Planning passes (test question) | Elapsed (s) | Agent input tokens | Agent output tokens |",
             "|---|---|---|---|---|---|---|"]
    for s in summary:
        mode = "extractiveData" if s["level"] == "minimal" else "answerSynthesis"
        lines.append(f"| {s['level']} | {mode} | {s['passed']}/{s['total']} | {s['planning']} | "
                     f"{s['elapsed']:.0f} | {s['in']:,} | {s['out']:,} |")
    changed = {qid: v for qid, v in per_question.items() if len(set(v.values())) > 1}
    lines += ["", "## Questions whose result changed between settings", ""]
    if changed:
        lines += ["| Question | " + " | ".join(args.levels) + " |", "|---" * (len(args.levels) + 1) + "|"]
        for qid, v in sorted(changed.items()):
            lines.append(f"| {qid} | " + " | ".join("pass" if v.get(l) else "FAIL" for l in args.levels) + " |")
    else:
        lines.append("None - every question gave the same pass/fail result at every setting.")
    lines += ["", "## Recommendation", "",
              "_Write one paragraph: the setting you would ship and the trade-off you accepted._", ""]

    out = RESULTS_DIR / "e2-retrieval-effort.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:6 + len(summary)]))
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
