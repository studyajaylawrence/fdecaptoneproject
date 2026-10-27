# E7 · Handle a policy that was updated

**Difficulty** Hard · **Time** ~50 min · **Proves** it behaves sensibly when the corpus disagrees with itself

## The situation

Hospital policy changes. For a while, both versions exist — the 2026 escalation policy says a
critical potassium must be phoned within 30 minutes, and a new 2027 revision says 20. A system
that silently picks one is more dangerous than one that says "these disagree".

## What to do

1. Create a revised version of an existing Contoso policy in your sandbox folder: same document
   ID, a later version and effective date, and **one changed threshold**.
2. Add it to your knowledge base so both versions are retrievable.
3. Ask the question that both documents answer.
4. Make the agent do the right thing: surface that two versions disagree, cite **both** with
   their versions and effective dates, and defer rather than choosing.

## Acceptance test

- The answer names both documents, both versions, and both values.
- It does not silently pick one.
- It is routed for clinician review.
- The 37 base questions (19 + fairness pairs) still pass.

## Worth thinking about

You could solve this at retrieval time (only index the current version), in the instructions
(prefer the later effective date), or by deferring. Each is defensible and each fails
differently — retrieval hides the conflict, instructions guess, deferral costs a clinician's
time. Which would you actually ship in a hospital, and what would you monitor afterwards?
