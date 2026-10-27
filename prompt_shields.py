"""Azure AI Content Safety Prompt Shields - model-based prompt-injection detection.

The regexes in safeguards.py only catch phrasings someone thought of in advance ("ignore
previous instructions"). Prompt Shields is a trained classifier that also catches
paraphrases, role-play, encodings and other languages. It runs on both attack surfaces:

    user prompt   screen_prompt()     before the model; an attack is blocked like a regex hit
    documents     screen_documents()  on what the knowledge base retrieved (ask_agent
                                      `_context`); an indirect attack withholds the answer
                                      and holds it for clinician review

Both fail closed: if the service cannot be reached the request is held for review, never
released unchecked.

Endpoint: CONTENT_SAFETY_ENDPOINT, defaulting to the shared Foundry (AI Services) resource,
which serves Content Safety. Auth is Entra ID (AzureCliCredential) - no keys. The signed-in
identity needs the "Cognitive Services User" role on that resource.

Only redacted text is sent (screen_input runs first), so PHI never leaves for this call
either (CHS-POL-004 minimum necessary).
"""
from __future__ import annotations

import functools
import os
import random
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass, field

import requests

from safeguards import Screening

API_VERSION = os.environ.get("CONTENT_SAFETY_API_VERSION", "2024-09-01")
_SCOPE = "https://cognitiveservices.azure.com/.default"
_TIMEOUT = 15
_MAX_ATTEMPTS = 3

# Service limits per call: prompt <= 10K characters; up to 5 documents, 10K characters total.
MAX_CHARS = 10_000
MAX_DOCUMENTS = 5
# Long documents are split with an overlap, so an instruction that straddles a split point is
# still seen whole in one piece.
_OVERLAP = 500

_DOC_ID = re.compile(r"CHS-(?:POL|PATH)-\d{3}")


class ShieldsUnavailable(RuntimeError):
    """Prompt Shields could not give a verdict (network, auth, throttling, bad response)."""


@dataclass
class ShieldResult:
    prompt_attack: bool
    document_attacks: list[int] = field(default_factory=list)   # indexes into `documents`


def _endpoint() -> str:
    # Imported lazily: lab_config exits without a .env, and the offline tests import this module.
    endpoint = os.environ.get("CONTENT_SAFETY_ENDPOINT")
    if not endpoint:
        import lab_config as cfg  # noqa: PLC0415
        endpoint = cfg.CU_URI
    return endpoint.rstrip("/")


@functools.lru_cache(maxsize=1)
def _credential():
    from azure.identity import AzureCliCredential  # noqa: PLC0415
    return AzureCliCredential()


def _pieces(documents: Sequence[str]) -> list[tuple[int, str]]:
    """Split documents into (original index, text) pieces of at most MAX_CHARS each."""
    pieces: list[tuple[int, str]] = []
    step = MAX_CHARS - _OVERLAP
    for index, text in enumerate(documents):
        if not text:
            continue
        for start in range(0, max(len(text) - _OVERLAP, 1), step):
            pieces.append((index, text[start:start + MAX_CHARS]))
    return pieces


def _batches(pieces: list[tuple[int, str]]) -> list[list[tuple[int, str]]]:
    """Pack pieces into calls of at most MAX_DOCUMENTS pieces and MAX_CHARS characters."""
    batches: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    size = 0
    for piece in pieces:
        if current and (len(current) == MAX_DOCUMENTS or size + len(piece[1]) > MAX_CHARS):
            batches.append(current)
            current, size = [], 0
        current.append(piece)
        size += len(piece[1])
    if current:
        batches.append(current)
    return batches


def _post(user_prompt: str, documents: list[str]) -> dict:
    url = f"{_endpoint()}/contentsafety/text:shieldPrompt"
    body = {"userPrompt": user_prompt[:MAX_CHARS], "documents": documents}
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            headers = {"Authorization": f"Bearer {_credential().get_token(_SCOPE).token}"}
            response = requests.post(url, params={"api-version": API_VERSION}, headers=headers,
                                     json=body, timeout=_TIMEOUT)
        except Exception as exc:   # network or credential failure: no verdict
            if attempt == _MAX_ATTEMPTS:
                raise ShieldsUnavailable(type(exc).__name__) from exc
        else:
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError as exc:
                    raise ShieldsUnavailable("invalid response") from exc
            if response.status_code not in (408, 429) and response.status_code < 500:
                # 4xx (e.g. 401/403 missing role): retrying will not help.
                raise ShieldsUnavailable(f"HTTP {response.status_code}")
            if attempt == _MAX_ATTEMPTS:
                raise ShieldsUnavailable(f"HTTP {response.status_code}")
        time.sleep(2 ** attempt * 0.5 + random.uniform(0, 0.5))
    raise ShieldsUnavailable("no attempts made")   # unreachable; keeps type checkers happy


def check(user_prompt: str, documents: Sequence[str] = ()) -> ShieldResult:
    """Run Prompt Shields on a prompt and any documents. Raises ShieldsUnavailable on failure."""
    batches = _batches(_pieces(documents)) or [[]]
    prompt_attack = False
    flagged: set[int] = set()
    for batch in batches:
        payload = _post(user_prompt, [text for _, text in batch])
        try:
            prompt_attack |= bool(payload["userPromptAnalysis"]["attackDetected"])
            analyses = payload.get("documentsAnalysis") or []
            if len(analyses) != len(batch):
                raise ShieldsUnavailable("documentsAnalysis does not match documents sent")
            flagged.update(index for (index, _), a in zip(batch, analyses) if a["attackDetected"])
        except (KeyError, TypeError) as exc:
            raise ShieldsUnavailable("unexpected response shape") from exc
    return ShieldResult(prompt_attack, sorted(flagged))


# --------------------------------------------------------------------- pipeline adapters
def screen_prompt(text: str) -> Screening:
    """User-prompt attack check for the (already redacted) question."""
    screening = Screening(text=text)
    try:
        attack = check(text).prompt_attack
    except ShieldsUnavailable as exc:
        screening.hold = True
        screening.reasons.append(f"Prompt Shields unavailable ({exc}) - held for review")
        return screening
    if attack:
        screening.blocked = True
        screening.reasons.append("Prompt Shields: user prompt attack detected")
    return screening


def screen_documents(question: str, documents: Sequence[str]) -> Screening:
    """Document (indirect) attack check on retrieved knowledge-base content.

    `blocked` means a retrieved document carries injected instructions: the answer may be
    manipulated and must not be released or shown as a draft. The reason names the affected
    CHS documents so the corpus owner can investigate.
    """
    screening = Screening(text="")
    if not documents:
        return screening
    try:
        flagged = check(question, documents).document_attacks
    except ShieldsUnavailable as exc:
        screening.hold = True
        screening.reasons.append(f"Prompt Shields unavailable for retrieved documents ({exc}) - held for review")
        return screening
    if flagged:
        ids = sorted({doc for i in flagged for doc in _DOC_ID.findall(documents[i])})
        where = ", ".join(ids) if ids else f"{len(flagged)} retrieved passage(s)"
        screening.blocked = True
        screening.reasons.append(f"Prompt Shields: injected instructions detected in retrieved document ({where})")
    return screening
