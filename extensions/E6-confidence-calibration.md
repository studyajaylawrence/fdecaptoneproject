# E6 · Check whether "High" means high

**Difficulty** Hard · **Time** ~45 min · **Proves** self-reported confidence is worth something

## The situation

Your agent labels its own confidence, and your oversight rule routes on that label. If "High"
is sometimes wrong, the label is worse than useless — it is actively routing bad answers past a
human.

## What to do

1. For every evaluation question, put the claimed confidence beside whether the answer actually
   passed its checks. `results.jsonl` has both.
2. Build the calibration table: for answers labelled High, Moderate and Low, what share were
   actually correct?
3. Find the disagreements — a High that failed, or a Low that was perfectly correct — and read
   what the agent said. The pattern is usually in the wording of your confidence rule.
4. Tighten the rule and re-run. Aim for **no High-confidence failures at all**; a Low that turns
   out correct is a much cheaper mistake.

## Acceptance test

- A calibration table across all three labels.
- Zero answers labelled High that fail their checks.
- A sentence explaining what you changed, and why that class of error happened.

## Worth thinking about

An agent that labels everything Moderate is perfectly calibrated and completely useless — every
answer goes to a human, so the assistant saves nobody any time. Calibration and usefulness pull
against each other. Where did you put the line, and could you defend it to a clinical safety
lead?
