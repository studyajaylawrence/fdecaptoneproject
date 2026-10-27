# E5 · Put a price and a latency budget on it

**Difficulty** Moderate · **Time** ~45 min · **Proves** it could survive a finance conversation

## The situation

Contoso likes the assistant and asks the obvious question: what does it cost to run, and how
fast is it? A care coordinator will not wait 30 seconds for a policy lookup.

## What to do

1. **Measure what you already collect.** Every call returns `_telemetry` with input and output
   tokens; `results.jsonl` has it for every question. Add wall-clock timing per question.
2. **Model the cost.** Take current published per-token prices for your models and work out cost
   per question and per 1,000 questions. Remember the knowledge base makes its own model calls
   for query planning and synthesis — that cost is real and easy to forget.
3. **Try to make it cheaper.** Re-create your agent on `gpt-5.4-mini` instead of `gpt-5.2`,
   re-run the evaluation, and compare quality against cost.
4. **Recommend.** One configuration, with the trade-off stated plainly.

## Acceptance test

A table of cost and latency per question for at least two configurations, the evaluation score
for each, and a recommendation you would defend to someone paying the bill.

## Worth thinking about

Latency and cost are not evenly distributed: a deferral is cheap and fast, a multi-document
synthesis is neither. An average hides that. What does the slowest 10% look like, and is that
the case a clinician actually hits?
