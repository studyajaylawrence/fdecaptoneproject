# Extensions — going deeper on UC004

You have a working, grounded, evaluated assistant. These challenges take it from *working* to
*defensible*: the questions an evaluation panel asks when the demo has already gone well.

Each one is independent. Pick what interests you — nobody is expected to do all seven.

| # | Challenge | Difficulty | Rough time | What it proves |
|---|---|---|---|---|
| [E1](E1-extend-the-corpus.md) | Add your own policy and route between sources | Moderate | 45 min | The corpus is not fixed, and routing is a design decision |
| [E2](E2-tune-retrieval.md) | Measure retrieval effort instead of guessing | Moderate | 40 min | You can justify a configuration with numbers |
| [E3](E3-red-team.md) | Red-team your own agent | Hard | 60 min | It holds up against someone trying to break it |
| [E4](E4-verify-citations.md) | Prove the citations are real | Hard | 45 min | A cited answer is not the same as a grounded one |
| [E5](E5-cost-and-latency.md) | Put a price and a latency budget on it | Moderate | 45 min | It could survive a finance conversation |
| [E6](E6-confidence-calibration.md) | Check whether "High" means high | Hard | 45 min | Self-reported confidence is worth something |
| [E7](E7-conflicting-guidance.md) | Handle a policy that was updated | Hard | 50 min | It behaves sensibly when the corpus disagrees with itself |

## The rule that applies to all of them

**Finish with evidence, not an assertion.** Every challenge has an acceptance test. A panel
will believe a number and a repeatable command; it will not believe "it seemed to work".

**And do not break what already works.** After any change, run the base evaluation again:

```powershell
python step4_evaluate.py --local-only
```

37/37 must still pass. A change that fixes one thing and quietly breaks two is a regression,
and regressions are the most common way these systems degrade in production.

## Implemented in this repository

*Implementation and design notes: Ajay Lawrence.*

Every challenge has a runnable implementation. Run the scripts **from the repository root**
with the venv active. They reuse the step functions instead of copying them, so the lab
configuration stays in one place. Summaries are written to `extensions/results/*.md` as
evidence; raw `*.jsonl` results are git-ignored.

| # | Files | Run | Acceptance test → how it is checked |
|---|---|---|---|
| E1 | `sandbox/CHS-POL-007-…md`, `sandbox_corpus.py`, `e1-questions.jsonl` | `python extensions/sandbox_corpus.py sync --include e1`, then `python step4_evaluate.py --local-only --extra extensions/e1-questions.jsonl` | e1-01/e1-02 must cite CHS-POL-007; e1-03 (sepsis) must still cite CHS-PATH-010; the base questions (37) still pass in the same run |
| E2 | `e2_tune_retrieval.py`, `e2_compare.py` | Scripted: `python extensions/e2_tune_retrieval.py`. Manual, one setting at a time: see [E2 manual scenario](#e2-manual-scenario) | Writes the three-row table (pass rate, planning passes, elapsed, tokens) plus the questions that changed between settings. The scripted run restores your knowledge base afterwards; after the manual run, restore it with `--effort medium`. |
| E3 | `adversarial-examples.jsonl` (10 cases) | `python step4_evaluate.py --local-only --adversarial` (agent) and `... --pipeline --adversarial` (full path) | Every adversarial case passes; the base questions (37) still pass. For router paraphrases, `python router_review.py --questions extensions/router-paraphrases.jsonl` lists every miss |
| E4 | `e4_verify_citations.py` | `python extensions/e4_verify_citations.py`, then `... --make-broken` | Zero INVENTED for your agent; the deliberately broken agent (`agent-<alias>-broken`) is caught |
| E5 | `e5_cost_latency.py`, `prices.json` | Evaluate each configuration with `--results`, fill in `prices.json`, then `python extensions/e5_cost_latency.py gpt-5.2=… gpt-5.4-mini=…` | Cost per question and per 1,000, p50/p90/max latency, by-category breakdown and the slowest 10%, for each configuration |
| E6 | `e6_calibration.py` | `python extensions/e6_calibration.py` | Calibration table over High/Moderate/Low; exits 1 if any High answer failed |
| E7 | `sandbox/CHS-POL-002-…-v7.md`, `e7-questions.jsonl` (8 cases), agent rule 23, `step3_assistant.version_conflicts` | `python extensions/sandbox_corpus.py sync --include e1 e7`, then `python step4_evaluate.py --local-only --extra extensions/e7-questions.jsonl` | e7-01–03 state both INR values (> 5.0 and > 4.5), cite both versions and are escalated; e7-04–06 (unchanged sections: RRT 2255, out-of-hours 4500, potassium) are answered without a false conflict; e7-07/08 resist "use the newest" and "v6.0 is withdrawn" pressure |

### E2 manual scenario

Same agent, same questions; only `retrievalReasoningEffort` changes. `--kb-only` re-creates
the knowledge base without re-ingesting the corpus (`minimal` automatically uses
`extractiveData`). At `minimal` the knowledge base's `/retrieve` endpoint rejects chat
`messages` ("Use intents input instead"), so the test query is sent as a semantic search
intent and always reports 0 planning passes. `--test` checks the deployed effort and picks the
request shape itself.

```powershell
python step1_create_knowledge.py --kb-only --effort minimal     # note "query planning passes: N"
Measure-Command { python step4_evaluate.py --local-only --results extensions/results/e2-minimal.jsonl | Out-Default } | Select TotalSeconds
python step1_create_knowledge.py --kb-only --effort low
Measure-Command { python step4_evaluate.py --local-only --results extensions/results/e2-low.jsonl | Out-Default } | Select TotalSeconds
python step1_create_knowledge.py --kb-only --effort medium
Measure-Command { python step4_evaluate.py --local-only --results extensions/results/e2-medium.jsonl | Out-Default } | Select TotalSeconds
python extensions/e2_compare.py --planning minimal=<n> low=<n> medium=<n> --elapsed minimal=<s> low=<s> medium=<s>
```

`e2_compare.py` writes `results/e2-retrieval-effort.md`: the totals table, then every question
whose pass/fail, failed checks, confidence, cited documents or review flag differed between
settings. Questions to read closely: q01 (bundle table and time zero are in separate chunks),
the hypertension local-vs-national questions (need two documents), and q19 (out of corpus).
Finish with `--effort medium` to restore the shipped setting.

### Design notes

- **E1: routing, not merging.** The new policy lives in a second knowledge source over
  `sandbox/<alias>/` only (`folderPath`). `step1.create_knowledge_source()` refuses a sandbox
  source without that folder, so other participants' files can never be indexed. `retrievalInstructions` say which source covers
  isolation and hand hygiene and which covers sepsis timing. The policy points to CHS-PATH-010
  for blood-culture timing instead of restating it, so neither source contradicts the other.
- **E2: `minimal` runs with `extractiveData`.** `minimal` cannot synthesize answers, so its
  row also changes what the agent receives. Agent tokens are measured; the knowledge base's own
  planning and synthesis tokens are not in `_telemetry`. `minimal` also accepts only
  `intents` input on `/retrieve`, not chat `messages`; `lab_search.retrieve(..., intents=True)`
  sends that shape, and `e2_tune_retrieval.py` uses it for the `minimal` row.
- **E3: hardening was in code as well as prompts.** a08 (prompt extraction) is now blocked at
  input. a09 (a dose request framed as "training slides") and a10 ("already approved, mark as
  reviewed") now route as acute. The 19 base questions route exactly as before.
- **E4: two different notions of "grounded".** The groundedness evaluator judges whether the
  answer follows from the context. The checker proves each cited document exists **and** was
  retrieved. Answers with no captured context are reported UNVERIFIABLE, not passed.
- **E5: no prices are shipped.** `prices.json` starts empty and the script refuses to run
  until you enter current prices. Out-of-date numbers would be worse than none.
- **E7: the change is chosen not to break the base 19.** Version 7.0 changes only the INR
  critical value, which no base question asks about. The step 3 code check holds any answer
  where two versions of one document were cited **or retrieved**, so while E7 is loaded, every
  CHS-POL-002 answer goes to a clinician. That is deliberate (the corpus disagrees with
  itself). Run `sync --include e1` to take version 7.0 out again.

Clean up with `python extensions/sandbox_corpus.py remove`. The `-mini` and `-broken` agent
variants can stay; the trainer removes the shared backend.

## Your sandbox

You have write access to one folder of your own in the shared storage account:

```
sandbox/<your-alias>/...
```

The approved `corpus` container stays read-only for everyone — that is deliberate, and it is
also why E1 uses the sandbox rather than adding to the corpus directly. Anything you upload
lives under your alias and cannot disturb anyone else's work.

## How these are assessed

They map onto the capstone's own criteria:

| Criterion | Challenges that speak to it |
|---|---|
| Solution design & architecture | E1, E7 |
| Technical implementation | E1, E4, E6 |
| Deployment readiness | E2, E3, E5 |
| Business value | E5 |
| Innovation | E4, E7 |
| Presentation & defence | all of them — bring the numbers |
