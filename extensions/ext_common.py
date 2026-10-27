"""Shared helpers for the extension scripts. Nothing to edit here.

Author: Ajay Lawrence - implementation of the shared extension helpers (see extensions/README.md).

Run extension scripts from the repository root, e.g. `python extensions/e6_calibration.py`.
Blob access uses the same keyless AzureCliCredential as the rest of the lab (no account keys,
no shelling out to `az`), via the Blob Storage REST API so no extra package is needed.
"""
from __future__ import annotations

import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests  # noqa: E402
from azure.identity import AzureCliCredential  # noqa: E402

import lab_config as cfg  # noqa: E402

SANDBOX_CONTAINER = "sandbox"
_credential = AzureCliCredential()
_HEADERS = {"x-ms-version": "2023-11-03"}


def _blob_url(container: str, name: str = "") -> str:
    return f"https://{cfg.STORAGE_ACCOUNT}.blob.core.windows.net/{container}" + (f"/{name}" if name else "")


def _auth() -> dict[str, str]:
    token = _credential.get_token("https://storage.azure.com/.default").token
    return {**_HEADERS, "Authorization": f"Bearer {token}"}


def upload_blob(container: str, name: str, path: pathlib.Path) -> None:
    response = requests.put(
        _blob_url(container, name), timeout=60, data=path.read_bytes(),
        headers={**_auth(), "x-ms-blob-type": "BlockBlob", "Content-Type": "text/markdown; charset=utf-8"},
    )
    response.raise_for_status()


def delete_blob(container: str, name: str) -> None:
    response = requests.delete(_blob_url(container, name), headers=_auth(), timeout=60)
    if response.status_code not in (202, 404):
        response.raise_for_status()


def list_blobs(container: str, prefix: str = "") -> list[str]:
    names: list[str] = []
    marker = ""
    while True:
        params = {"restype": "container", "comp": "list", "prefix": prefix}
        if marker:
            params["marker"] = marker
        response = requests.get(_blob_url(container), params=params, headers=_auth(), timeout=60)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        names += [el.text for el in root.iter("Name") if el.text]
        marker = (root.findtext("NextMarker") or "").strip()
        if not marker:
            return names


def sandbox_source_name() -> str:
    return f"{cfg.KS_NAME}-sandbox"
