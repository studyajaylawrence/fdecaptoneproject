"""Shared configuration for the UC004 lab. Nothing to edit here - set values in .env.

Every object you create is named after your LAB_ALIAS so 36 people can share one backend
without colliding.
"""
from __future__ import annotations

import os
import re
import sys

from dotenv import load_dotenv

load_dotenv()

# Windows consoles default to cp1252, and the clinical corpus is full of characters like
# "≥" and "≤". Without this, printing a perfectly good answer raises UnicodeEncodeError.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):   # already wrapped, or not a real console
        pass

ALIAS = os.environ.get("LAB_ALIAS", "").strip().lower()
if not ALIAS or ALIAS == "changeme":
    sys.exit("Set LAB_ALIAS in your .env file to your own short name before running this.")
if not re.fullmatch(r"[a-z0-9]{2,12}", ALIAS):
    sys.exit("LAB_ALIAS must be 2-12 characters, lowercase letters and digits only.")

# Shared backend
PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
SEARCH_ENDPOINT = os.environ["SEARCH_ENDPOINT"]
SEARCH_API_VERSION = os.environ.get("SEARCH_API_VERSION", "2026-08-01-preview")
STORAGE_ACCOUNT = os.environ["STORAGE_ACCOUNT"]
CORPUS_CONTAINER = os.environ.get("CORPUS_CONTAINER", "corpus")
FOUNDRY_NAME = os.environ["FOUNDRY_NAME"]
PROJECT_NAME = os.environ["PROJECT_NAME"]
RESOURCE_GROUP = os.environ["RESOURCE_GROUP"]
SUBSCRIPTION_ID = os.environ["SUBSCRIPTION_ID"]

CHAT_DEPLOYMENT = os.environ.get("CHAT_DEPLOYMENT", "gpt-5.2")
MINI_DEPLOYMENT = os.environ.get("MINI_DEPLOYMENT", "gpt-5.4-mini")
EMBED_DEPLOYMENT = os.environ.get("EMBED_DEPLOYMENT", "text-embedding-3-large")

AOAI_URI = f"https://{FOUNDRY_NAME}.openai.azure.com"
CU_URI = f"https://{FOUNDRY_NAME}.cognitiveservices.azure.com"
STORAGE_RESOURCE_ID = (
    f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}"
    f"/providers/Microsoft.Storage/storageAccounts/{STORAGE_ACCOUNT}"
)
PROJECT_RESOURCE_ID = (
    f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}"
    f"/providers/Microsoft.CognitiveServices/accounts/{FOUNDRY_NAME}/projects/{PROJECT_NAME}"
)

# Your own objects
KS_NAME = f"ks-{ALIAS}"
KB_NAME = f"kb-{ALIAS}"
CONNECTION_NAME = f"conn-{ALIAS}"
AGENT_NAME = f"agent-{ALIAS}"
REVIEW_TABLE = f"review{ALIAS}"          # table names: letters and digits only

KB_MCP_URL = f"{SEARCH_ENDPOINT}/knowledgebases/{KB_NAME}/mcp?api-version={SEARCH_API_VERSION}"


def summary() -> str:
    return (
        f"alias           : {ALIAS}\n"
        f"knowledge source: {KS_NAME}\n"
        f"knowledge base  : {KB_NAME}\n"
        f"connection      : {CONNECTION_NAME}\n"
        f"agent           : {AGENT_NAME}\n"
        f"review table    : {REVIEW_TABLE}\n"
        f"project         : {PROJECT_ENDPOINT}\n"
        f"search          : {SEARCH_ENDPOINT}"
    )


if __name__ == "__main__":
    print(summary())
