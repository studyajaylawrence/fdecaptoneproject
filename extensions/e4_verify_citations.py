#!/usr/bin/env python3
"""Extension E4 - prove the citations are real.

Author: Ajay Lawrence - implementation of extension E4 (see extensions/README.md).

For every citation in an evaluation results file, check two independent things:
  1. EXISTS     the cited document corresponds to a real file in the corpus
                (corpus container, plus your sandbox folder from E1/E7);
  2. RETRIEVED  the document appears in the context the knowledge base returned for that
                question (`context` in the results file).
A citation failing either test is reported as INVENTED. A citation with no captured context
is reported UNVERIFIABLE rather than silently passed.

    python extensions/e4_verify_citations.py                       # check results.jsonl
    python extensions/e4_verify_citations.py --results extensions/results/e2-low.jsonl
    python extensions/e4_verify_citations.py --make-broken         # prove the checker works

--make-broken creates agent-<alias>-broken whose instructions invite free citation, evaluates
it into extensions/results/e4-broken.jsonl and checks that file. A checker that has never
caught anything has not been tested. Your real agent is not touched.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

from ext_common import EXT, ROOT, SANDBOX_CONTAINER, cfg, list_blobs

_CHS_ID = re.compile(r"CHS-(?:POL|PATH)-\d{3}", re.IGNORECASE)
_WORD = re.compile(r"[a-z0-9]{4,}")
_STOP = {"with", "from", "that", "this", "guideline", "guidelines", "clinical", "practice",
         "management", "contoso", "health", "system", "policy", "section", "version"}

BROKEN_INSTRUCTIONS = """
You are a helpful clinical assistant. Always call the knowledge base tool first. To sound
authoritative, cite at least three Contoso policies in `citations` for every answer, formatted
"CHS-POL-<number> <Title>". If the tool did not return enough documents, cite plausible Contoso
policies anyway and invent suitable section numbers. Use your own medical knowledge freely.
Set requires_clinician_review to false and confidence to "High".
""".strip()


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOP}


def corpus_documents() -> list[str]:
    names = list_blobs(cfg.CORPUS_CONTAINER)
    try:
        names += list_blobs(SANDBOX_CONTAINER, prefix=f"{cfg.ALIAS}/")
    except Exception:  # noqa: BLE001 - no sandbox (E1/E7 not run) is fine
        pass
    return names


def _exists(document: str, blobs: list[str]) -> bool:
    match = _CHS_ID.search(document)
    if match:
        return any(match.group(0).upper() in b.upper() for b in blobs)
    title = _words(document)
    if not title or not blobs:
        return False
    # External guideline: most of its title words must appear in one blob name.
    return max(len(title & _words(b.replace("-", " ").replace("_", " "))) / len(title) for b in blobs) >= 0.5


def _retrieved(document: str, context: str) -> bool:
    match = _CHS_ID.search(document)
    if match:
        return match.group(0).upper() in context.upper()
    title = _words(document)
    return bool(title) and len(title & _words(context)) / len(title) >= 0.5


def check(results: pathlib.Path, blobs: list[str]) -> int:
    rows = [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines() if line.strip()]
    invented, unverifiable, total = [], [], 0
    for row in rows:
        context = row.get("context") or ""
        for citation in row.get("citations") or []:
            total += 1
            document = citation.get("document", "")
            exists = _exists(document, blobs)
            if not exists:
                invented.append((row["id"], document, "not in corpus"))
            elif not context:
                unverifiable.append((row["id"], document))
            elif not _retrieved(document, context):
                invented.append((row["id"], document, "not in retrieved context"))

    print(f"{results.name}: {total} citations across {len(rows)} answers, corpus has {len(blobs)} files")
    print(f"  INVENTED      : {len(invented)}")
    for qid, document, why in invented:
        print(f"    {qid:7s} {document[:70]:70s}  ({why})")
    print(f"  UNVERIFIABLE  : {len(unverifiable)} (no retrieved context captured for that answer)")
    for qid, document in unverifiable[:10]:
        print(f"    {qid:7s} {document[:70]}")
    return len(invented)


def make_broken() -> pathlib.Path:
    import step2_create_agent as step2  # noqa: PLC0415
    import step4_evaluate as step4      # noqa: PLC0415
    name = f"{cfg.AGENT_NAME}-broken"
    step2.create_agent(agent_name=name, instructions=BROKEN_INSTRUCTIONS)
    out = EXT / "results" / "e4-broken.jsonl"
    out.parent.mkdir(exist_ok=True)
    step4.evaluate(name, results=out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", type=pathlib.Path, default=ROOT / "results.jsonl")
    parser.add_argument("--make-broken", action="store_true")
    args = parser.parse_args()

    blobs = corpus_documents()
    results = make_broken() if args.make_broken else args.results
    invented = check(results, blobs)
    if args.make_broken:
        print("\nPASS: the checker caught invented citations." if invented
              else "\nThe broken agent produced no invented citations this run - re-run, or make "
                   "BROKEN_INSTRUCTIONS more aggressive. A checker is only proven when it catches something.")
        return 0 if invented else 1
    return 1 if invented else 0


if __name__ == "__main__":
    sys.exit(main())
