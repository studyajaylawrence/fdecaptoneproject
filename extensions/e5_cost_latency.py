#!/usr/bin/env python3
"""Extension E5 - put a price and a latency budget on it.

Author: Ajay Lawrence - implementation of extension E5 (see extensions/README.md).

Reads one or more evaluation results files (each `label=path`) and reports, per configuration:
cost per question and per 1,000 questions, latency p50 / p90 / max, the slowest 10%, a
per-category breakdown, and the behaviour score. Writes extensions/results/e5-cost-latency.md.

1. Produce results for each configuration, e.g.
       python step4_evaluate.py --local-only --results extensions/results/e5-gpt52.jsonl
       python step2_create_agent.py --name agent-<alias>-mini --model gpt-5.4-mini
       python step4_evaluate.py --local-only --name agent-<alias>-mini --results extensions/results/e5-mini.jsonl
2. Put CURRENT published prices into extensions/prices.json (USD per 1M tokens). This script
   deliberately ships no prices: stale numbers are worse than none.
3. python extensions/e5_cost_latency.py gpt-5.2=extensions/results/e5-gpt52.jsonl \
                                        gpt-5.4-mini=extensions/results/e5-mini.jsonl

The label must match a model key in prices.json. Knowledge-base planning and synthesis calls
are NOT in the agent's token telemetry; `kb_tokens_per_question` in prices.json lets you add
an estimate (measure it from the knowledge base's activity log) so that cost is not forgotten.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys

# Offline analysis only: no Azure or .env needed, so ext_common is not imported.
EXT = pathlib.Path(__file__).resolve().parent
ROOT = EXT.parent

PRICES = EXT / "prices.json"


def _pct(values: list[float], p: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, round(p / 100 * len(ordered)) - 1))]


def _cost(row: dict, price: dict, kb: dict) -> float:
    t = row.get("_telemetry") or {}
    agent = ((t.get("input_tokens") or 0) * price["input"] + (t.get("output_tokens") or 0) * price["output"])
    kb_cost = kb.get("input", 0) * kb.get("input_price", 0) + kb.get("output", 0) * kb.get("output_price", 0)
    return (agent + kb_cost) / 1_000_000


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", nargs="+", metavar="LABEL=RESULTS")
    args = parser.parse_args()

    prices = json.loads(PRICES.read_text(encoding="utf-8"))
    kb = prices.get("kb_tokens_per_question", {})
    lines = ["# E5 - cost and latency", "",
             "Prices (USD per 1M tokens) from `extensions/prices.json`, recorded on "
             f"{prices.get('prices_checked_on', '?')}. Source: {prices.get('source', '?')}.", "",
             "| Configuration | Behaviour checks | Cost / question (mean) | Cost / 1,000 questions | p50 latency (s) | p90 latency (s) | Max (s) |",
             "|---|---|---|---|---|---|---|"]
    details: list[str] = []
    for spec in args.runs:
        label, _, path = spec.partition("=")
        price = prices["models"].get(label)
        if not price or price.get("input") is None:
            sys.exit(f"No price for '{label}' in {PRICES} - fill it in from the current price list.")
        rows = [json.loads(l) for l in pathlib.Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
        costs = [_cost(r, price, kb) for r in rows]
        latency = [r.get("elapsed_s") or 0.0 for r in rows]
        passed = sum(r["passed"] for r in rows)
        mean = statistics.mean(costs)
        lines.append(f"| {label} | {passed}/{len(rows)} | ${mean:.5f} | ${mean * 1000:.2f} | "
                     f"{_pct(latency, 50):.1f} | {_pct(latency, 90):.1f} | {max(latency):.1f} |")

        details += ["", f"## {label} - by category", "",
                    "| Category | n | Mean cost | Mean latency (s) | Max latency (s) |", "|---|---|---|---|---|"]
        for category in sorted({r["category"] for r in rows}):
            idx = [i for i, r in enumerate(rows) if r["category"] == category]
            details.append(f"| {category} | {len(idx)} | ${statistics.mean(costs[i] for i in idx):.5f} | "
                           f"{statistics.mean(latency[i] for i in idx):.1f} | {max(latency[i] for i in idx):.1f} |")
        slow = sorted(range(len(rows)), key=lambda i: latency[i], reverse=True)[:max(1, len(rows) // 10)]
        details += ["", f"Slowest 10% ({label}):", ""]
        details += [f"- {rows[i]['id']} ({rows[i]['category']}, {latency[i]:.1f}s): {rows[i]['query'][:90]}" for i in slow]

    lines += details + ["", "## Recommendation", "",
                        "_One configuration, with the quality/cost trade-off stated plainly._", ""]
    out = EXT / "results" / "e5-cost-latency.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwritten to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
