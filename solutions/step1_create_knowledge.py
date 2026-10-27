#!/usr/bin/env python3
"""LAB PART 1 - ground the assistant on the approved corpus with Foundry IQ.

You create two objects on the shared Azure AI Search service:

  knowledge source  - points at the approved corpus in blob storage, extracts and embeds it
  knowledge base    - plans queries over one or more sources and returns cited results

Run:
    python step1_create_knowledge.py            # create both, wait for ingestion, test
    python step1_create_knowledge.py --test     # just run the test query again
    python step1_create_knowledge.py --delete   # remove your objects

REFERENCE SOLUTION. Compare with your own version rather than starting here.
"""
from __future__ import annotations

import argparse

import lab_config as cfg
import lab_search as search


def create_knowledge_source() -> dict:
    body = {
        "name": cfg.KS_NAME,
        "kind": "azureBlob",
        "description": (
            "Contoso Health System approved clinical corpus: VA/DoD clinical practice "
            "guidelines and CHS internal policies and pathways."
        ),
        "azureBlobParameters": {
            "connectionString": f"ResourceId={cfg.STORAGE_RESOURCE_ID};",
            "containerName": cfg.CORPUS_CONTAINER,
            "ingestionParameters": {
                # Content Understanding reads the dosing tables and pathway flowcharts in
                # the guideline PDFs; "minimal" is faster but loses that structure.
                "contentExtractionMode": "standard",
                "aiServices": {"uri": cfg.CU_URI},
                "embeddingModel": {
                    "kind": "azureOpenAI",
                    "azureOpenAIParameters": {
                        "resourceUri": cfg.AOAI_URI,
                        "deploymentId": cfg.EMBED_DEPLOYMENT,
                        "modelName": cfg.EMBED_DEPLOYMENT,
                    },
                },
                "chatCompletionModel": {
                    "kind": "azureOpenAI",
                    "azureOpenAIParameters": {
                        "resourceUri": cfg.AOAI_URI,
                        "deploymentId": cfg.MINI_DEPLOYMENT,
                        "modelName": cfg.MINI_DEPLOYMENT,
                    },
                },
            },
        },
    }
    print(f"Creating knowledge source {cfg.KS_NAME}")
    return search.call("PUT", f"/knowledgesources/{cfg.KS_NAME}", body)


def create_knowledge_base() -> dict:
    body = {
        "name": cfg.KB_NAME,
        "description": "Grounding over the Contoso Health System approved clinical corpus.",
        "knowledgeSources": [{"name": cfg.KS_NAME}],
        "models": [{
            "kind": "azureOpenAI",
            "azureOpenAIParameters": {
                "resourceUri": cfg.AOAI_URI,
                "deploymentId": cfg.MINI_DEPLOYMENT,
                "modelName": cfg.MINI_DEPLOYMENT,
            },
        }],
        # "medium" plans the query, applies a semantic classifier and retries once, which
        # is what lets one answer combine a national guideline with a local policy.
        "retrievalReasoningEffort": {"kind": "medium"},

        # "answerSynthesis" returns a written answer with reference ids, which is what
        # gives the agent cited grounding. "extractiveData" would return raw chunks.
        "outputMode": "answerSynthesis",

        "answerInstructions": (
            "Answer only from the retrieved approved corpus. Cite the source document for "
            "every claim. If the corpus does not contain the answer, say so explicitly."
        ),
    }
    print(f"Creating knowledge base {cfg.KB_NAME}")
    return search.call("PUT", f"/knowledgebases/{cfg.KB_NAME}", body)


def test_retrieval() -> None:
    question = "What must happen within 60 minutes of time zero in the Contoso adult sepsis pathway?"
    print(f"\nTest question: {question}\n")
    result = search.retrieve(question)

    for entry in result.get("response", []):
        for content in entry.get("content", []):
            print(content.get("text", "")[:1200])

    references = result.get("references", [])
    print(f"\n{len(references)} references")
    for reference in references[:5]:
        source = reference.get("blobUrl") or reference.get("citationUrl") or ""
        print(f"  [{reference.get('id')}] {source.rsplit('/', 1)[-1][:90]}")

    planning = [a for a in result.get("activity", []) if a.get("type") == "modelQueryPlanning"]
    print(f"\nquery planning passes: {len(planning)}")


def delete() -> None:
    for path in (f"/knowledgebases/{cfg.KB_NAME}", f"/knowledgesources/{cfg.KS_NAME}"):
        try:
            search.call("DELETE", path)
            print(f"deleted {path}")
        except RuntimeError as exc:
            print(f"could not delete {path}: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true", help="only run the test query")
    parser.add_argument("--delete", action="store_true", help="delete your knowledge base and source")
    args = parser.parse_args()

    if args.delete:
        delete()
        return
    if args.test:
        test_retrieval()
        return

    source = create_knowledge_source()
    created = source.get("azureBlobParameters", {}).get("createdResources", {})
    indexer = created.get("indexer", f"{cfg.KS_NAME}-indexer")
    create_knowledge_base()

    print(f"\nWaiting for ingestion ({indexer}). The corpus is ~230 pages, so this takes a few minutes.")
    search.wait_for_ingestion(indexer)
    print("ingestion complete")

    test_retrieval()


if __name__ == "__main__":
    main()
