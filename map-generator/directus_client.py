import os

import requests

DIRECTUS_URL = os.environ["DIRECTUS_URL"].rstrip("/")
DIRECTUS_TOKEN = os.environ["DIRECTUS_TOKEN"]
UPLOAD_FOLDER_ID = os.environ.get("DIRECTUS_UPLOAD_FOLDER_ID")

_session = requests.Session()
_session.headers.update({"Authorization": f"Bearer {DIRECTUS_TOKEN}"})


def get_item(item_id: int) -> dict:
    resp = _session.get(
        f"{DIRECTUS_URL}/items/itinerari/{item_id}",
        params={"fields": "traccia_gpx,mappa_statica,profilo_altimetrico"},
    )
    resp.raise_for_status()
    return resp.json()["data"]


def download_asset(file_id: str) -> bytes:
    resp = _session.get(f"{DIRECTUS_URL}/assets/{file_id}")
    resp.raise_for_status()
    return resp.content


def delete_file(file_id: str) -> None:
    resp = _session.delete(f"{DIRECTUS_URL}/files/{file_id}")
    if resp.status_code not in (200, 204, 404):
        resp.raise_for_status()


def upload_file(filename: str, content: bytes, content_type: str = "image/png") -> str:
    data = {"folder": UPLOAD_FOLDER_ID} if UPLOAD_FOLDER_ID else None
    resp = _session.post(
        f"{DIRECTUS_URL}/files",
        data=data,
        files={"file": (filename, content, content_type)},
    )
    resp.raise_for_status()
    return resp.json()["data"]["id"]


def patch_item(item_id: int, fields: dict) -> None:
    resp = _session.patch(f"{DIRECTUS_URL}/items/itinerari/{item_id}", json=fields)
    resp.raise_for_status()
