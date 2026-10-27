# Reference solutions

Completed versions of the three files that carry TODOs in the lab.

**Try it yourself first.** The lab is four hours of thinking, not typing — the value is in
working out *why* each choice is what it is, and the evaluation in Part 4 will tell you
honestly whether your version works. Come here when you are stuck, when you want to compare
your approach with another, or when you are short on time and would rather spend it on the
parts you find interesting.

| File | Covers |
|---|---|
| `step1_create_knowledge.py` | TODO 1–3: extraction mode, retrieval reasoning effort, output mode |
| `step2_create_agent.py` | TODO 1–3: the agent instructions, the MCP tool wiring, `tool_choice` |
| `step3_assistant.py` | The `should_hold()` oversight rule |

## Using these

Copy a file over the one in the repository root and run it normally:

```powershell
Copy-Item solutions\step1_create_knowledge.py .\step1_create_knowledge.py -Force
python step1_create_knowledge.py
```

Your `.env` and `LAB_ALIAS` still apply, so everything you create is still named after you.

## The parts worth reading rather than copying

- **The agent instructions in `step2_create_agent.py`.** The deferral rule is deliberately
  strict: when the agent defers, the answer contains *only* the deferral and the escalation
  route. Without that, the model defers and then helpfully volunteers the guideline content it
  just retrieved — which is exactly what CHS-POL-001 forbids.
- **`tool_choice="required"`.** `"auto"` lets the model answer from its own medical knowledge.
  That single word is the difference between a grounded assistant and a plausible one.
- **`should_hold()` fails closed.** An answer with no citation is ungrounded by definition, so
  it is held even when the agent sounds confident.
