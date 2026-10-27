# E2 · Measure retrieval effort instead of guessing

**Difficulty** Moderate · **Time** ~40 min · **Proves** you can justify a configuration with numbers

## The situation

You chose `medium` reasoning effort in Part 1 because the guide suggested it. A reviewer asks
what it costs you, and whether `low` would do. "It felt better" is not an answer.

## What to do

1. Re-create your knowledge base at each setting — `minimal`, `low`, `medium` — and after each
   one run the full behaviour evaluation.
2. For each setting record: behaviour checks passed, query-planning passes seen in
   `step1_create_knowledge.py --test`, wall-clock time for the evaluation, and the input/output
   tokens reported in `results.jsonl` under `_telemetry`.
3. Note which *specific* questions change answer quality between settings — that is more
   informative than the totals.

## Acceptance test

A three-row table with pass rate, planning passes, elapsed time and tokens, plus a one-paragraph
recommendation naming the setting you would ship and the trade-off you accepted.

## Worth thinking about

`minimal` does no LLM planning at all and cannot synthesize answers. If it still scores well on
this corpus, that tells you something real about the corpus — probably that the questions map
cleanly onto single documents. Would that hold with 500 documents instead of 15?
