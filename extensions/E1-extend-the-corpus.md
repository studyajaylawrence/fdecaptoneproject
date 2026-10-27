# E1 · Add your own policy, and teach the agent when to use it

**Difficulty** Moderate · **Time** ~45 min · **Proves** the corpus is a design decision, not a fixture

## The situation

Contoso's Infection Prevention team has written a new ward-level protocol. It is not in the
approved corpus yet, and it partly overlaps with the sepsis pathway you already ground on. Your
assistant needs to use it — without losing track of which document an answer came from.

## What to do

1. **Write the document.** A short fictional Contoso policy, in the same style as the ones in
   `reference/policies/` — an ID, a version, an effective date, and rules specific enough to be
   checkable. Give it at least two facts nothing else in the corpus states.

2. **Upload it to your sandbox folder:**

   ```powershell
   az storage blob upload --account-name <storage-account> --auth-mode login `
     -c sandbox -n "<your-alias>/CHS-POL-0XX-your-policy.md" -f .\your-policy.md
   ```

3. **Create a second knowledge source** over *your folder only*. A blob knowledge source takes a
   `folderPath`, so point it at `<your-alias>` inside the `sandbox` container — otherwise you
   index everyone else's work too.

4. **Add it to your knowledge base** alongside the original, and use `retrievalInstructions` to
   tell the retriever when to prefer which source.

## Acceptance test

- A question only your new document can answer returns a **High** confidence answer that cites
  **your** document by name.
- A question about the sepsis pathway still cites `CHS-PATH-010`, not your new file.
- `python step4_evaluate.py --local-only` still passes **37/37**.

## Worth thinking about

Two sources that partly overlap is the normal case in a hospital, not an edge case. What should
happen when both could answer? Retrieval instructions are one answer; a single merged corpus is
another. Be ready to say which you chose and why.
