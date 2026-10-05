"""
Moodle Draft Files Manager service.
Handles uploading, deleting, and renaming files staged in Moodle draft areas.
"""

import os
import secrets
from typing import Optional

import requests


class MoodleDraftFileManager:
    """Manages files in Moodle's user draft area (repository_ajax and draftfiles_manager)."""

    def __init__(self, session: requests.Session):
        self.session = session

    def upload(
        self,
        file_path: str,
        itemid: str,
        ctx_id: str,
        sesskey: str,
        new_name: Optional[str] = None,
    ) -> bool:
        """Upload a local file to Moodle's draft files repository."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Attachment file not found: {file_path}")

        if not itemid:
            raise ValueError("Moodle draft item ID (itemid) is required for file uploads.")

        if not ctx_id:
            raise ValueError("Moodle context ID (ctx_id) is required for file uploads.")

        if not sesskey:
            raise ValueError("Session key (sesskey) is required for file uploads.")

        upload_filename = new_name if new_name else os.path.basename(file_path)
        upload_url = "https://ekursy.put.poznan.pl/repository/repository_ajax.php?action=upload"
        client_id = secrets.token_hex(6)

        payload = {
            "action": "upload",
            "repo_id": "4",  # Upload a file repo
            "sesskey": sesskey,
            "client_id": client_id,
            "itemid": itemid,
            "ctx_id": ctx_id,
            "savepath": "/",
            "license": "allrightsreserved",
            "author": "",
            "title": upload_filename,
        }

        with open(file_path, "rb") as f:
            files = {"repo_upload_file": f}
            resp = self.session.post(upload_url, data=payload, files=files, timeout=60)
            resp.raise_for_status()
            if "error" in resp.text:
                raise RuntimeError(f"File upload failed: {resp.text}")
        return True

    def delete(
        self,
        filename: str,
        itemid: str,
        ctx_id: str,
        sesskey: str,
    ) -> bool:
        """Delete a file from Moodle's draft files manager."""
        if not itemid:
            raise ValueError("Moodle draft item ID (itemid) is required.")
        if not ctx_id:
            raise ValueError("Moodle context ID (ctx_id) is required.")
        if not sesskey:
            raise ValueError("Session key (sesskey) is required.")

        delete_url = "https://ekursy.put.poznan.pl/repository/draftfiles_manager.php"
        params = {
            "ctx_id": ctx_id,
            "itemid": itemid,
            "env": "filemanager",
            "course": "1",
            "maxbytes": "0",
            "areamaxbytes": "-1",
            "maxfiles": "-1",
            "subdirs": "0",
            "sesskey": sesskey,
            "action": "deletedraft",
            "draftpath": "/",
            "filename": filename,
        }
        resp = self.session.get(delete_url, params=params, timeout=30)
        resp.raise_for_status()
        return True

    def rename(
        self,
        filename: str,
        new_name: str,
        itemid: str,
        ctx_id: str,
        sesskey: str,
    ) -> bool:
        """Rename an existing file in Moodle's draft files manager."""
        if not new_name:
            raise ValueError("New name must be provided to rename an attachment.")
        if not itemid:
            raise ValueError("Moodle draft item ID (itemid) is required.")
        if not ctx_id:
            raise ValueError("Moodle context ID (ctx_id) is required.")
        if not sesskey:
            raise ValueError("Session key (sesskey) is required.")

        rename_url = "https://ekursy.put.poznan.pl/repository/draftfiles_manager.php"
        params = {
            "ctx_id": ctx_id,
            "itemid": itemid,
            "env": "filemanager",
            "course": "1",
            "maxbytes": "0",
            "areamaxbytes": "-1",
            "maxfiles": "-1",
            "subdirs": "0",
            "sesskey": sesskey,
            "action": "rename",
            "draftpath": "/",
        }
        post_data = {"newfilename": new_name, "filename": filename, "draftpath": "/"}
        resp = self.session.post(rename_url, params=params, data=post_data, timeout=30)
        resp.raise_for_status()
        if "errormessage" in resp.text or "errorcode" in resp.text:
            raise RuntimeError(f"File renaming failed: {resp.text}")
        return True


def upload_draft_file(
    session: requests.Session,
    file_path: str,
    itemid: str,
    ctx_id: str,
    sesskey: str,
    new_name: Optional[str] = None,
) -> bool:
    """Backwards-compatible standalone function for uploading draft files."""
    mgr = MoodleDraftFileManager(session)
    return mgr.upload(file_path, itemid, ctx_id, sesskey, new_name)
