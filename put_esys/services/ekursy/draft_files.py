import os
from typing import Optional

import requests


def upload_draft_file(
    session: requests.Session,
    file_path: str,
    itemid: str,
    ctx_id: str,
    sesskey: str,
    new_name: Optional[str] = None,
) -> bool:
    """Upload a file to Moodle's draft files repository."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Attachment file not found: {file_path}")

    if not itemid:
        raise Exception("Moodle draft item ID (itemid) is required for file uploads.")

    if not ctx_id:
        raise Exception("Moodle context ID (ctx_id) is required for file uploads.")

    if not sesskey:
        raise Exception("Session key (sesskey) is required for file uploads.")

    upload_filename = new_name if new_name else os.path.basename(file_path)

    upload_url = "https://ekursy.put.poznan.pl/repository/repository_ajax.php?action=upload"
    payload = {
        "action": "upload",
        "repo_id": "4",  # Upload a file repo
        "sesskey": sesskey,
        "client_id": "6a11b8466c708",  # Hardcoded unique client ID
        "itemid": itemid,
        "ctx_id": ctx_id,
        "savepath": "/",
        "license": "allrightsreserved",
        "author": "",
        "title": upload_filename,
    }

    with open(file_path, "rb") as f:
        files = {"repo_upload_file": f}
        resp = session.post(upload_url, data=payload, files=files)
        resp.raise_for_status()
        if "error" in resp.text:
            raise Exception(f"File upload failed: {resp.text}")
    return True
