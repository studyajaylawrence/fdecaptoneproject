# UC004 · Clinical Knowledge Grounding Agent — Lab

Microsoft FDE Use-Case Pack · Wipro AI Academy
**L200 → L300 · 4 hours · Microsoft Foundry + Foundry IQ**

Build a clinical knowledge assistant that answers only from an approved corpus of clinical
guidelines and hospital policy, cites what it used, labels its own confidence, hands every
patient-specific question to a clinician, and is then measured for groundedness.

> **Training environment.** "Contoso Health System" and every CHS document are fictional,
> written for this lab. The VA/DoD Clinical Practice Guidelines in the corpus are real,
> public-domain US federal publications. **Nothing here may be used for real patient care.**

## Start here

1. Open **[docs/lab-guide.md](docs/lab-guide.md)** and follow it from Part 0.
2. You will need the **lab environment handout** from your trainer — it has the endpoints,
   resource names and subscription id that go into your `.env` file. This repository ships
   placeholders only.

Quick setup on your lab VM (PowerShell as Administrator):

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\setup-windows.ps1
```

The script creates `.env` from `.env.example`. Open `.env`, paste in the handout values, set
`LAB_ALIAS` to your lab username, and continue with Part 1 of the guide.

## What you will build

```
  approved corpus (blob: corpus/)          sandbox (blob: sandbox/<alias>/)        E1, E7
        │  Content Understanding                 │  your folder only (folderPath)
        │  extraction + embeddings               │  CHS-POL-007 (E1), CHS-POL-002 v7.0 (E7)
        ▼                                        ▼
  knowledge source ks-<alias> ───┐    ┌─── knowledge source ks-<alias>-sandbox    step 1
                                 ▼    ▼
                     knowledge base kb-<alias> (Foundry IQ)                       step 1
                         │  effort: medium (E2 measures minimal / low / medium)
                         │  retrieval instructions: hybrid queries + source routing (E1)
                         │  cited answer synthesis; both versions surfaced (E7)
                         │  MCP, authenticated with a managed identity - no keys
                         ▼
                      your Foundry agent  (tool_choice="required", JSON contract) step 2
                      rules 1-23 (23 = conflicting document versions, E7)
                      variants: -mini model (E5), -broken citation test (E4)
                         ▲
  requester question     │
        │                │
        ▼                │
  screen_input ── blocked (prompt injection / oversized) ──► refused, audited    step 3
        │  PHI redacted before the model, queue or logs see it
        │  Prompt Shields on the redacted question (attack ──► refused, audited)
        ▼
  router: acute / clinical / administrative   (acute patterns hardened by E3)
        │
        ▼
  agent answer ──► screen_output (PHI, prompt leak) ──► Prompt Shields on retrieved documents ──► should_hold (fail closed)
                                                        citations · corpus + retrieved-context check
                                                        version conflict (E7) · route rules
                                                            │
                               ┌────────────────────────────┴───────────┐
                               ▼                                        ▼
                  released with AI disclosure          clinician review queue ──► review console
                  (grounded, cited)                    (deferred, Low, uncited,    (named reviewer,
                                                        acute, PHI, conflict,       note, decided once,
                                                        safeguard; route stored)    "router missed" flag)
                               │                                        │
                               └──────────► audit.log (PHI-free) ◄──────┤
                                                                        ▼
                                                 router_review.py ──► router-review.md
                                                 (clinician worksheet for _ACUTE_PATTERNS)

  evaluation and evidence                                                         step 4
  questions.jsonl (19 + 9 fairness pairs) + e1 / e7 questions + adversarial set (10, E3)
        │  step4_evaluate.py  [--pipeline] [--adversarial] [--extra FILE] [--results FILE]
        ▼
  results.jsonl (answers, checks, context, telemetry, latency)
        ├──► fairness pairs ──────► parity report (fairness.py, agent rule 20)
        ├──► E2 effort sweep ─────► extensions/results/e2-retrieval-effort.md
        │     (scripted: e2_tune_retrieval.py · manual: step1 --kb-only + e2_compare.py)
        ├──► E4 citation checker ─► invented / unretrieved citations (proven on -broken agent)
        ├──► E5 cost & latency ───► extensions/results/e5-cost-latency.md
        └──► E6 calibration ──────► extensions/results/e6-calibration.md

  tests/test_safety_rules.py   router · safeguards · should_hold · Prompt Shields handling ·
                               fairness pairs · router review - offline (no Azure)
```

Every rule in the agent's prompt has a matching check in code, so an answer that breaks a rule
is still caught if the model ignores it. See
[docs/security-and-responsible-ai.md](docs/security-and-responsible-ai.md).

## Architecture enhancements

Changes made after the core lab. They don't change any lab TODO. Checkpoint 4 now covers the
fairness pairs (37/37 instead of 19/19), and Prompt Shields needs one extra role (see
[Requirements](#requirements)).

| Enhancement | Why | Where |
|---|---|---|
| **End-to-end evaluation** (`--pipeline`) | The base evaluation scores the agent only. `--pipeline` runs each question through the step 3 path (safeguards → router → agent → `should_hold`) as a dry run, with nothing queued or audited, and adds a `release_decision` check: answerable questions must be released, everything else held or blocked. This measures what requesters actually get. | `step4_evaluate.py`, `step3_assistant.handle(dry_run=True)` |
| **Red-team set in the evaluation** (`--adversarial`) | Adds the 10 prompts from `extensions/adversarial-examples.jsonl` to any run, so attacks are tested on every regression run, not only in extension E3. | `step4_evaluate.py` |
| **Retry with backoff, then fail closed** | Throttling (429), timeouts and 5xx errors are retried with exponential backoff and jitter (`AGENT_MAX_ATTEMPTS`, default 4). If every attempt fails, the answer is held for review instead of crashing. Previously one 429 aborted the parallel evaluation. | `ask_agent.py` |
| **Client reuse** | One Foundry client per agent per process, a shared credential with a cached token, and `create_table` once per process instead of on every queue call (a console refresh used to make five). | `ask_agent.py`, `review_queue.py` |
| **Safe concurrent review** | ETag-conditioned claim of a pending item: if two reviewers decide at once, one wins and the other is told. A failed write puts the item back. | `review_queue.decide` |
| **PHI redaction on every field** | Redaction now covers the model's `review_reason` and citations as well as the answer, and reviewer notes as well as edits. | `safeguards.screen_output`, `reviewer_app.py` |
| **Stricter router** | Bed or bay numbers, ages, and "do not route / just tell me" requests now route as acute (always held). So do specific result values, including "potassium reading of 6.5" and a bare "K 6.2", and "should I set / run / use" dose or infusion requests. "A patient" is no longer an acute signal ("my / this / the patient" still is): it wrongly held q04, a general referral question, so `--pipeline` could not reach 19/19. No answerable base question routes as acute. | `step3_assistant._ACUTE_PATTERNS` |
| **Fabricated citations held without context** | A cited CHS identifier must exist in the corpus (`KNOWN_DOCUMENT_IDS`, read from `reference/policies/` and `extensions/sandbox/`). Previously an invented "CHS-POL-999" was released whenever no retrieved context had been captured. Real identifiers with no captured context are still released, because answer synthesis can return no per-document text. | `step3_assistant._documents_in_context` |
| **Requester sees the outcome** | `--status` explains rejections and adds the AI disclosure to clinician-approved answers. | `step3_assistant.py` |
| **Extensions E1–E7 implemented** | Runnable scripts for all seven challenges, built on reusable step functions (`create_knowledge_source/base(...)`, `create_agent(name, model, instructions)`, `step4.evaluate(...)`) rather than copied code. See [extensions/README.md](extensions/README.md#implemented-in-this-repository). | `extensions/*.py`, steps 1–4 |
| **Prompt Shields** | Azure AI Content Safety Prompt Shields checks the redacted question before the model and every retrieved passage after it, catching paraphrased and indirect injection that the regexes miss. A user-prompt attack is refused; a document attack withholds the answer and holds it. If the service is unreachable or the identity lacks the Cognitive Services User role, the request is held (fail closed). The E1/E7 sandbox sync scans files before upload. | `prompt_shields.py`, `step3_assistant.handle`, `extensions/sandbox_corpus.py` |
| **Fairness measured** | Agent rule 20 is tested, not just stated: 9 question pairs differ only by sex, race, religion, insurance, housing, disability, gender identity or language. Step 4 fails a pair if the swap changes escalation, release, confidence, citations or the facts stated, and prints a side-by-side report. One pair checks that a distinction the corpus does cite (interpreter appointment length) is stated. | `questions.jsonl`, `fairness.py`, `step4_evaluate.py` |
| **Router review loop** | Review items now store the router's route and matched patterns (previously dropped by `enqueue`). Reviewers can tick "router missed this". `router_review.py` turns the queue into a worksheet for clinicians and measures acute recall on a paraphrase set (currently 0/12, which is the documented gap). | `review_queue.py`, `reviewer_app.py`, `router_review.py`, `extensions/router-paraphrases.jsonl` |
| **Offline safety tests** | 62 unit tests. They run in under a second with no Azure access and no `.env` (the agent, review queue and Prompt Shields service are stubbed). They cover base and red-team routing, PHI redaction, input blocking, prompt-leak blocking, every `should_hold` rule, Prompt Shields batching and fail-closed handling, the fairness pairs and comparison, and the router review worksheet. Run them after any change to patterns or rules. | `tests/test_safety_rules.py` |
| **Version-conflict hold (E7)** | Agent rule 23, plus a code check: if two versions of one CHS document are cited **or retrieved**, the answer is held, even if the model silently picked one. | `step2` rule 23, `step3_assistant.version_conflicts` |
| **Custom RAG tuning** | Hybrid-friendly query planning: exact IDs and terms for the keyword leg, paraphrase for the vector leg, and local CHS policy always retrieved alongside national guidance. Effort level is configurable (`RETRIEVAL_EFFORT`, `--kb-only --effort`) so E2 can measure it. | `step1_create_knowledge.RETRIEVAL_INSTRUCTIONS` |
| **Strict citation standard** | Three layers: the knowledge base cites exact IDs; agent rules 4–8 require `"<ID> <Title>"` + `"Section <n>"`, one entry per document; `citation_problems()` holds any malformed, duplicated or inline-marker citation. | step 1 `answerInstructions`, step 2 rules 4–8, `step3_assistant.citation_problems` |
| **Deterministic fairness and deferral form** | Fairness failures came from wording drift, not policy. Rule 20 now requires an identical answer when the corpus makes no distinction; rule 12 fixes the deferral form (Low, CHS-POL-001 + CHS-POL-002 Section 4); rule 9 counts several sections of one document as one source; rule 3 fixes the out-of-corpus sentence. | `step2_create_agent.INSTRUCTIONS` |
| **Groundedness evaluation within payload limits** | The cloud evaluation previously sent every item in one run and failed with HTTP 413. Context is now capped per item and items are split into size-bounded runs whose scores are combined. | `step4_evaluate.cloud_groundedness` |
| **Sandbox scope guard** | `create_knowledge_source()` refuses a source over any container but the approved corpus unless `folderPath` is your alias, so you can never index other participants' sandbox files. | `step1_create_knowledge.create_knowledge_source` |

**Still on the production backlog**: Entra ID sign-in for the review console, the audit log
shipped to Log Analytics or immutable storage, Azure AI Language PII detection in place of
regular expressions, least-privilege RBAC per identity, the indirect-attack Prompt Shield on the
agent's model deployment, clinician review of the acute router patterns (tooling is in place;
the review itself is a clinical task), and repeated sampling of the fairness pairs. Details are in
[docs/security-and-responsible-ai.md](docs/security-and-responsible-ai.md#known-limits-production-backlog).

## What is in this repository

| Path | What it is |
|---|---|
| `docs/lab-guide.md` | The lab, in six parts, with checkpoints and troubleshooting |
| `docs/design-decisions.md` | The choice made at each TODO and why — for the Part 6 defence |
| `docs/security-and-responsible-ai.md` | Defence in depth, Responsible AI principles mapped to controls, threats, how to verify, known limits |
| `docs/UC004-Architecture.docx` | Word document explaining the solution architecture, for reviewers and the defence |
| `.env.example` | Template for your `.env` — placeholders only, never commit `.env` |
| `step1_create_knowledge.py` | Part 1 — create your knowledge source and knowledge base (has TODOs) |
| `step2_create_agent.py` | Part 2 — create the connection and your grounded agent (has TODOs) |
| `step3_assistant.py` | Part 3 — human oversight routing (has a TODO) |
| `step4_evaluate.py` | Part 4 — behaviour checks and groundedness evaluation |
| `reviewer_app.py` | The clinician review console (Streamlit) |
| `safeguards.py` | Input/output screening (prompt injection, PHI redaction, prompt-leak block), AI disclosure, PHI-free audit log |
| `prompt_shields.py` | Azure AI Content Safety Prompt Shields client: user-prompt and document attack checks, fail closed |
| `lab_config.py`, `lab_search.py`, `ask_agent.py`, `review_queue.py` | Helper modules — nothing to edit |
| `questions.jsonl` | The 19 evaluation questions plus 9 fairness pairs (18 questions that differ only by a demographic attribute) |
| `fairness.py` | Compares each fairness pair's decisions in step 4 (agent rule 20) |
| `router_review.py` | Clinician worksheet for reviewing `_ACUTE_PATTERNS`: likely router misses from the review queue, and recall on question files such as `extensions/router-paraphrases.jsonl` |
| `reference/policies/` | The fictional Contoso policies. **Read CHS-POL-001 first — it is the specification your agent must satisfy.** |
| `setup-windows.ps1` | One-time VM setup |
| `tests/` | Offline unit tests for the safety layer (router, safeguards, release rules, Prompt Shields handling, fairness, router review) — no Azure needed |
| `solutions/` | Reference solutions — try it yourself first, then compare |
| `extensions/` | Seven deeper challenges for when the core lab is done, plus `router-paraphrases.jsonl` (acute questions the router should catch) |

## Finished the lab?

The core lab gets you a working, grounded, evaluated assistant. **[extensions/](extensions/README.md)**
takes it from *working* to *defensible* — seven independent challenges covering retrieval tuning,
red-teaming, citation verification, cost and latency, confidence calibration and conflicting
policy versions. Each has an acceptance test, so you finish with evidence rather than an assertion.

Nobody is expected to do all seven. Pick the ones you would want to be asked about.

## Requirements

- A Windows lab VM with Python 3.12, the Azure CLI and VS Code (the lab image has these).
- An account that is a member of the lab participant group, so you can create agents and
  knowledge bases in the shared backend.
- **Cognitive Services User** on the Foundry resource (or on `CONTENT_SAFETY_ENDPOINT`) for
  Prompt Shields. Without it every step 3 answer is held with "Prompt Shields unavailable
  (HTTP 403)": fail closed, by design. Ask your trainer if you see that.

## Commands

```powershell
python lab_config.py                      # show the names your alias generates
python step1_create_knowledge.py          # create + ingest + test your knowledge base
python step1_create_knowledge.py --test   # re-run the test query (sent as a search intent
                                          # if the knowledge base is at effort minimal)
python step1_create_knowledge.py --delete # delete your knowledge objects
python step1_create_knowledge.py --kb-only --effort low
                                          # E2: re-create only the knowledge base at one
                                          # effort level (no re-ingestion), then run the test
python step2_create_agent.py              # create your connection and agent
python step2_create_agent.py --ask "..."  # ask your agent
python step3_assistant.py "..."           # ask, with oversight routing
python step3_assistant.py --status <id>   # check a held item
streamlit run reviewer_app.py             # clinician review console
python step4_evaluate.py                  # evaluate your agent (+ cloud groundedness)
python step4_evaluate.py --local-only     # behaviour checks only - Checkpoint 4 is 37/37
python step4_evaluate.py --local-only --pipeline --adversarial
                                          # full requester path + red-team set (dry run)
python -m unittest discover tests -v      # offline safety tests (no Azure needed)
python router_review.py                   # clinician worksheet from the review queue
python router_review.py --questions questions.jsonl extensions/router-paraphrases.jsonl
                                          # router recall, misses and false positives

# Extensions (see extensions/README.md)
python extensions/sandbox_corpus.py sync --include e1 [e7]   # E1/E7: add sandbox documents
python extensions/sandbox_corpus.py remove                   # back to the base corpus
python extensions/e2_tune_retrieval.py                       # E2: effort sweep table
python extensions/e2_compare.py --planning minimal=0 low=1 medium=2 --elapsed minimal=<s> low=<s> medium=<s>
                                                             # E2 (manual): compare e2-<level>.jsonl files
python extensions/e4_verify_citations.py [--make-broken]     # E4: citation checker
python extensions/e5_cost_latency.py LABEL=RESULTS ...       # E5: cost + latency (fill prices.json)
python extensions/e6_calibration.py                          # E6: calibration table
```

Optional environment settings (in `.env`): `RETRIEVAL_EFFORT` (default `medium`),
`AGENT_MAX_ATTEMPTS` (default `4`), `MAX_QUESTION_CHARS` (default `2000`), `AUDIT_LOG`
(default `audit.log`), `CONTENT_SAFETY_ENDPOINT` (default: your Foundry resource,
`https://<FOUNDRY_NAME>.cognitiveservices.azure.com`), `CONTENT_SAFETY_API_VERSION` (default
`2024-09-01`), `EVAL_MAX_CONTEXT_CHARS` (default `6000`) and `EVAL_MAX_BATCH_BYTES` (default
`150000`) for the cloud groundedness evaluation (lower them if you see HTTP 413 "document was
too large").

## Licence and attribution

The VA/DoD Clinical Practice Guidelines referenced by this lab are works of the US federal
government and are in the public domain. The Contoso Health System documents in
`reference/policies/` are fictional training content written for this lab.
