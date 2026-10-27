#!/usr/bin/env python3
"""Extensions E1 and E7 - add documents to the knowledge base through a sandbox source.

Author: Ajay Lawrence - implementation of extensions E1 and E7 (see extensions/README.md).

E1  adds CHS-POL-007 (ward infection prevention), which overlaps the sepsis pathway.
E7  adds CHS-POL-002 version 7.0 alongside version 6.0 (one changed threshold: INR).

Run from the repository root:
    python extensions/sandbox_corpus.py sync --include e1        # E1 only
    python extensions/sandbox_corpus.py sync --include e1 e7     # E1 + E7
    python extensions/sandbox_corpus.py remove                   # back to the base lab

`sync` uploads the chosen files to sandbox/<alias>/, removes the other managed files, rebuilds
a second knowledge source over YOUR folder only (folderPath), waits for ingestion, and points
the knowledge base at both sources with routing instructions. The knowledge source is rebuilt
rather than updated so a removed file cannot linger in the index.

Then evaluate:
    python step4_evaluate.py --local-only --extra extensions/e1-questions.jsonl
    python step4_evaluate.py --local-only --extra extensions/e7-questions.jsonl

Note: while the E7 file is present, every answer drawn from CHS-POL-002 can see two versions
and step 3 holds it for review (version_conflicts). That is deliberate - see the E7 notes in
docs/design-decisions.md. Run `sync --include e1` to take E7 out again.
"""
from __future__ import annotations

import argparse

from ext_common import EXT, SANDBOX_CONTAINER, cfg, delete_blob, list_blobs, sandbox_source_name, upload_blob

import lab_search as search
import prompt_shields
import step1_create_knowledge as step1

DOCS = {
    "e1": EXT / "sandbox" / "CHS-POL-007-ward-infection-prevention-and-isolation.md",
    "e7": EXT / "sandbox" / "CHS-POL-002-clinical-escalation-and-on-call-v7.md",
}

# E1: tell the retriever when to prefer which source. Overlap is the normal case in a hospital.
ROUTING_INSTRUCTIONS = (
    "Source routing: knowledge source '{sandbox}' holds Contoso documents added after the base "
    "corpus, including CHS-POL-007 Ward Infection Prevention and Isolation Protocol. Use it for "
    "isolation, precautions, hand hygiene and infection-control specimen questions. For sepsis "
    "screening, time zero and the first-hour bundle use CHS-PATH-010 in '{base}'. When a "
    "question spans both, retrieve from both and keep every statement tied to the document it "
    "came from. If both sources hold versions of the same document ID, retrieve both versions."
)


def _blob_name(path) -> str:
    return f"{cfg.ALIAS}/{path.name}"


def _reset_kb_and_source() -> None:
    """Point the KB back at the base source, then drop the sandbox source (KB first: it references it)."""
    step1.create_knowledge_base()
    try:
        search.call("DELETE", f"/knowledgesources/{sandbox_source_name()}")
        print(f"deleted knowledge source {sandbox_source_name()}")
    except RuntimeError:
        pass


def _shield_documents(paths) -> None:
    """Refuse to ingest a document that Prompt Shields flags for injected instructions.

    Scanned before anything is uploaded, so a poisoned file never reaches the index. If the
    service is unavailable the sync stops (fail closed); step 3 still screens at query time.
    """
    paths = list(paths)
    texts = [p.read_text(encoding="utf-8") for p in paths]
    result = prompt_shields.check("Summarise this Contoso policy document.", texts)
    if result.document_attacks:
        names = ", ".join(paths[i].name for i in result.document_attacks)
        raise SystemExit(f"Prompt Shields flagged injected instructions in: {names}. Not uploaded.")


def sync(include: list[str]) -> None:
    wanted = {_blob_name(DOCS[key]): DOCS[key] for key in include}
    _shield_documents(wanted.values())
    for name, path in wanted.items():
        upload_blob(SANDBOX_CONTAINER, name, path)
        print(f"uploaded {SANDBOX_CONTAINER}/{name}")
    managed = {_blob_name(p) for p in DOCS.values()}
    for name in list_blobs(SANDBOX_CONTAINER, prefix=f"{cfg.ALIAS}/"):
        if name in managed and name not in wanted:
            delete_blob(SANDBOX_CONTAINER, name)
            print(f"removed {SANDBOX_CONTAINER}/{name}")

    _reset_kb_and_source()
    source = step1.create_knowledge_source(
        name=sandbox_source_name(), container=SANDBOX_CONTAINER, folder=cfg.ALIAS,
        description="Contoso documents added after the base corpus (sandbox, extensions E1/E7).",
    )
    indexer = (source.get("azureBlobParameters", {}).get("createdResources", {})
               .get("indexer", f"{sandbox_source_name()}-indexer"))
    print(f"waiting for ingestion ({indexer})")
    search.wait_for_ingestion(indexer)

    step1.create_knowledge_base(
        sources=[cfg.KS_NAME, sandbox_source_name()],
        extra_instructions=ROUTING_INSTRUCTIONS.format(sandbox=sandbox_source_name(), base=cfg.KS_NAME),
    )
    print(f"knowledge base {cfg.KB_NAME} now grounds on {cfg.KS_NAME} + {sandbox_source_name()}")


def remove() -> None:
    _reset_kb_and_source()
    for path in DOCS.values():
        delete_blob(SANDBOX_CONTAINER, _blob_name(path))
    print("sandbox removed - knowledge base is back to the base corpus")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sync_parser = sub.add_parser("sync", help="upload documents and attach the sandbox source")
    sync_parser.add_argument("--include", nargs="+", choices=sorted(DOCS), default=["e1"])
    sub.add_parser("remove", help="detach the sandbox source and delete its files")
    args = parser.parse_args()
    if args.command == "sync":
        sync(args.include)
    else:
        remove()


if __name__ == "__main__":
    main()
