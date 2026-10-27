"""Thin helper for the Azure AI Search REST API (knowledge sources and knowledge bases).

Nothing to edit here.
"""
from __future__ import annotations

import json
import time
from typing import Any

import requests
from azure.identity import AzureCliCredential

import lab_config as cfg

# Reuse one credential so tokens are cached between calls. AzureCliCredential works on
# Windows, macOS and Linux - do not shell out to "az" directly, because on Windows az is a
# .cmd batch file and subprocess cannot execute it without a shell.
_credential = AzureCliCredential()


def token(scope: str = "https://search.azure.com/.default") -> str:
    return _credential.get_token(scope).token


def call(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{cfg.SEARCH_ENDPOINT}{path}"
    separator = "&" if "?" in path else "?"
    url = f"{url}{separator}api-version={cfg.SEARCH_API_VERSION}"
    response = requests.request(
        method, url,
        headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/json"},
        json=body, timeout=120,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"{method} {path} -> {response.status_code}\n{response.text[:800]}")
    if not response.content:
        return {}
    return json.loads(response.content.decode("utf-8", errors="replace"), strict=False)


def wait_for_ingestion(indexer_name: str, minutes: int = 20) -> None:
    """Block until the knowledge source has finished indexing the corpus."""
    deadline = time.time() + minutes * 60
    last = None
    while time.time() < deadline:
        status = call("GET", f"/indexers/{indexer_name}/status")
        result = status.get("lastResult") or {}
        state = result.get("status")
        line = f"  {status.get('status')} / {state}  processed={result.get('itemsProcessed')} failed={result.get('itemsFailed')}"
        if line != last:
            print(line, flush=True)
            last = line
        if state == "success":
            return
        if state in {"persistentFailure", "transientFailure"}:
            raise RuntimeError(f"ingestion failed: {str(result.get('errorMessage'))[:400]}")
        time.sleep(15)
    raise TimeoutError(f"ingestion did not finish within {minutes} minutes")


def retrieve(question: str, *, include_activity: bool = True, intents: bool = False) -> dict[str, Any]:
    """Query the knowledge base directly, without an agent.

    Set intents=True when the knowledge base uses retrievalReasoningEffort "minimal": that
    setting does no query planning, so it rejects "messages" and needs a search intent instead.
    """
    if intents:
        body: dict[str, Any] = {"intents": [{"type": "semantic", "search": question}]}
    else:
        body = {"messages": [{"role": "user", "content": [{"type": "text", "text": question}]}]}
    body["includeActivity"] = include_activity
    return call("POST", f"/knowledgebases/{cfg.KB_NAME}/retrieve", body)
