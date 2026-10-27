# E4 · Prove the citations are real

**Difficulty** Hard · **Time** ~45 min · **Proves** a cited answer is not automatically a grounded one

## The situation

Your agent cites its sources, and the groundedness evaluator scores 5/5. Neither of those
actually proves the cited *document* exists, or that the specific claim came from it. A citation
to a plausible-sounding policy that was never retrieved is the most dangerous failure this
system has, because it looks exactly like success.

## What to do

1. Write a checker that, for every question in the evaluation:
   - confirms each cited document name corresponds to a real file in the corpus
     (`az storage blob list`, or the references returned by retrieval);
   - confirms that document actually appears in the context the knowledge base returned for that
     question — `results.jsonl` has the retrieved context under `_context`.
2. Report any citation that fails either test.
3. **Prove your checker works** by breaking the agent on purpose: create a second agent version
   whose instructions invite it to cite freely, run the checker, and show it catching the
   invented citations. Then go back to your good version.

## Acceptance test

- The checker reports **zero** invented citations for your real agent.
- The checker demonstrably **catches** them on the deliberately broken one — a checker that has
  never caught anything has not been tested.

## Worth thinking about

You now have two different notions of "grounded": the evaluator's judgement that the answer
follows from the context, and your checker's evidence that the citation points at a document
that was really retrieved. They fail in different ways. Which would you monitor in production,
and how often?
