"""
Service for managing eKursy Private Files (https://ekursy.put.poznan.pl/user/files.php).
"""

import os
import re
import secrets
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from put_esys.models.files import PrivateFileItem, PrivateFilesList


@dataclass
class FilesSessionContext:
    """Holds metadata for an active Private Files draft session."""

    sesskey: str
    itemid: str
    ctx_id: str
    post_url: str
    client_id: str


def _format_size(size_bytes: int) -> str:
    """Format bytes into human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    for unit in ["KB", "MB", "GB", "TB"]:
        size_bytes /= 1024.0
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
    return f"{size_bytes:.1f} PB"


class PrivateFilesService:
    """Handles listing, uploading, downloading, and managing private files."""

    FILES_URL = "https://ekursy.put.poznan.pl/user/files.php"
    AJAX_URL = "https://ekursy.put.poznan.pl/repository/draftfiles_ajax.php"
    UPLOAD_URL = "https://ekursy.put.poznan.pl/repository/repository_ajax.php?action=upload"

    def __init__(self, session: requests.Session):
        self.session = session

    def _normalize_path(self, path: str) -> str:
        """Ensure path starts and ends with a forward slash."""
        if not path:
            return "/"
        path = path.strip().replace("\\", "/")
        if not path.startswith("/"):
            path = "/" + path
        if not path.endswith("/"):
            path = path + "/"
        return path

    def _get_session_context(self) -> FilesSessionContext:
        """Fetch the files.php page and extract form/draft metadata."""
        resp = self.session.get(self.FILES_URL, timeout=30)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Find form with _qf__core_user_form_private_files
        form = soup.find("input", {"name": "_qf__core_user_form_private_files"})
        if form:
            form = form.find_parent("form")

        if not form:
            # Fallback to any post form pointing to user/files.php
            for f in soup.find_all("form"):
                if "files.php" in f.get("action", "") and f.get("method", "").lower() == "post":
                    form = f
                    break

        if not form:
            raise RuntimeError("Could not find the Private Files form on eKursy.")

        post_url = form.get("action")
        if not post_url:
            post_url = self.FILES_URL
        elif not post_url.startswith("http"):
            post_url = urljoin(self.FILES_URL, post_url)

        sesskey_inp = form.find("input", {"name": "sesskey"})
        itemid_inp = form.find("input", {"name": "files_filemanager"})

        sesskey = sesskey_inp.get("value") if sesskey_inp else None
        itemid = itemid_inp.get("value") if itemid_inp else None

        if not sesskey:
            # Fallback search in page text
            sesskey_match = re.search(r'"sesskey":\s*"([^"]+)"', resp.text)
            if sesskey_match:
                sesskey = sesskey_match.group(1)

        if not itemid:
            itemid_match = re.search(r'"itemid":\s*(\d+)', resp.text)
            if itemid_match:
                itemid = itemid_match.group(1)

        if not sesskey:
            raise RuntimeError("Could not retrieve Moodle sesskey for Private Files.")
        if not itemid:
            raise RuntimeError("Could not retrieve Moodle draft item ID for Private Files.")

        ctx_match = re.search(r'"context":\s*\{[^}]*"id":\s*(\d+)', resp.text) or re.search(
            r'"contextid":\s*(\d+)', resp.text
        )
        ctx_id = ctx_match.group(1) if ctx_match else "1"

        client_id = secrets.token_hex(6)

        return FilesSessionContext(
            sesskey=sesskey,
            itemid=str(itemid),
            ctx_id=str(ctx_id),
            post_url=post_url,
            client_id=client_id,
        )

    def _commit_draft(self, ctx: FilesSessionContext) -> bool:
        """Save changes from the draft area permanently to user private files."""
        payload = {
            "sesskey": ctx.sesskey,
            "_qf__core_user_form_private_files": "1",
            "files_filemanager": ctx.itemid,
            "submitbutton": "Zapisz zmiany",
        }
        resp = self.session.post(ctx.post_url, data=payload, timeout=30)
        resp.raise_for_status()
        return True

    def list_files(self, path: str = "/", recursive: bool = False) -> PrivateFilesList:
        """List files and directories in private storage."""
        ctx = self._get_session_context()
        norm_path = self._normalize_path(path)

        all_items: List[PrivateFileItem] = []

        def _fetch_dir(dir_path: str):
            resp = self.session.post(
                f"{self.AJAX_URL}?action=list",
                data={
                    "sesskey": ctx.sesskey,
                    "client_id": ctx.client_id,
                    "itemid": ctx.itemid,
                    "filepath": dir_path,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            for entry in data.get("list", []):
                item_type = entry.get("type", "file")
                name = entry.get("filename") or entry.get("fullname", "")
                raw_size = int(entry.get("size", 0))
                filesize_str = entry.get("filesize") or _format_size(raw_size)

                item = PrivateFileItem(
                    filename=name,
                    filepath=dir_path,
                    fullname=entry.get("fullname") or name,
                    size=raw_size,
                    filesize=filesize_str,
                    type=item_type,
                    url=entry.get("url"),
                    datemodified=int(entry.get("datemodified"))
                    if entry.get("datemodified")
                    else None,
                    datecreated=int(entry.get("datecreated")) if entry.get("datecreated") else None,
                    author=entry.get("author"),
                    license=entry.get("license"),
                )
                all_items.append(item)

                if recursive and item_type == "folder":
                    sub_path = f"{dir_path}{name}/"
                    _fetch_dir(sub_path)

        _fetch_dir(norm_path)

        files = [i for i in all_items if i.type != "folder"]
        folders = [i for i in all_items if i.type == "folder"]
        total_sz = sum(f.size for f in files)

        return PrivateFilesList(
            path=norm_path,
            items=all_items,
            file_count=len(files),
            folder_count=len(folders),
            total_size=total_sz,
        )

    def download_file(
        self, remote_file: str, path: str = "/", output_path: Optional[str] = None
    ) -> str:
        """Download a file from private files to local storage."""
        norm_path = self._normalize_path(path)

        # Allow user to pass full remote path in remote_file
        if "/" in remote_file and not remote_file.startswith("/"):
            remote_file = "/" + remote_file

        if remote_file.startswith("/"):
            norm_path = self._normalize_path(os.path.dirname(remote_file))
            target_filename = os.path.basename(remote_file)
        else:
            target_filename = remote_file

        files_list = self.list_files(path=norm_path, recursive=False)
        target_item = None
        for item in files_list.items:
            if item.type != "folder" and (
                item.filename == target_filename or item.fullname == target_filename
            ):
                target_item = item
                break

        if not target_item or not target_item.url:
            raise FileNotFoundError(
                f"File '{target_filename}' not found in private files at '{norm_path}'."
            )

        dest_path = output_path if output_path else target_filename
        dest_dir = os.path.dirname(dest_path)
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)

        resp = self.session.get(target_item.url, stream=True, timeout=60)
        resp.raise_for_status()

        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return dest_path

    def upload_file(
        self, file_path: str, remote_path: str = "/", new_name: Optional[str] = None
    ) -> PrivateFileItem:
        """Upload a local file to eKursy private files and commit changes."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Local file not found: {file_path}")

        ctx = self._get_session_context()
        norm_path = self._normalize_path(remote_path)
        upload_title = new_name if new_name else os.path.basename(file_path)

        payload = {
            "action": "upload",
            "repo_id": "4",
            "sesskey": ctx.sesskey,
            "client_id": ctx.client_id,
            "itemid": ctx.itemid,
            "ctx_id": ctx.ctx_id,
            "savepath": norm_path,
            "license": "allrightsreserved",
            "author": "",
            "title": upload_title,
        }

        with open(file_path, "rb") as f:
            files = {"repo_upload_file": f}
            resp = self.session.post(self.UPLOAD_URL, data=payload, files=files, timeout=60)
            resp.raise_for_status()
            if "error" in resp.text:
                raise RuntimeError(f"File upload failed: {resp.text}")

        self._commit_draft(ctx)

        size = os.path.getsize(file_path)
        return PrivateFileItem(
            filename=upload_title,
            filepath=norm_path,
            fullname=upload_title,
            size=size,
            filesize=_format_size(size),
            type="file",
        )

    def create_folder(self, dirname: str, parent_path: str = "/") -> bool:
        """Create a new folder in private files storage."""
        if not dirname or "/" in dirname or "\\" in dirname:
            raise ValueError(f"Invalid folder name: '{dirname}'. Must not contain path separators.")

        ctx = self._get_session_context()
        norm_parent = self._normalize_path(parent_path)

        resp = self.session.post(
            f"{self.AJAX_URL}?action=mkdir",
            data={
                "sesskey": ctx.sesskey,
                "client_id": ctx.client_id,
                "itemid": ctx.itemid,
                "filepath": norm_parent,
                "newdirname": dirname,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"Failed to create folder '{dirname}': {data['error']}")

        self._commit_draft(ctx)
        return True

    def rename_file(self, filename: str, new_name: str, path: str = "/") -> bool:
        """Rename a file or folder in private files storage."""
        if not new_name or "/" in new_name or "\\" in new_name:
            raise ValueError(f"Invalid new name: '{new_name}'. Must not contain path separators.")

        ctx = self._get_session_context()
        norm_path = self._normalize_path(path)

        resp = self.session.post(
            f"{self.AJAX_URL}?action=updatefile",
            data={
                "sesskey": ctx.sesskey,
                "client_id": ctx.client_id,
                "itemid": ctx.itemid,
                "filepath": norm_path,
                "filename": filename,
                "newfilename": new_name,
                "newfilepath": norm_path,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and "error" in data:
            raise RuntimeError(f"Failed to rename '{filename}': {data['error']}")

        self._commit_draft(ctx)
        return True

    def move_file(self, filename: str, target_path: str, source_path: str = "/") -> bool:
        """Move a file or folder to another directory in private files storage."""
        ctx = self._get_session_context()
        norm_source = self._normalize_path(source_path)
        norm_target = self._normalize_path(target_path)

        resp = self.session.post(
            f"{self.AJAX_URL}?action=updatefile",
            data={
                "sesskey": ctx.sesskey,
                "client_id": ctx.client_id,
                "itemid": ctx.itemid,
                "filepath": norm_source,
                "filename": filename,
                "newfilename": filename,
                "newfilepath": norm_target,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and "error" in data:
            raise RuntimeError(
                f"Failed to move '{filename}' to '{norm_target}': {data['error']}"
            )

        self._commit_draft(ctx)
        return True

    def delete_file(self, filename: str, path: str = "/") -> bool:
        """Delete a file or folder from private files storage."""
        ctx = self._get_session_context()
        norm_path = self._normalize_path(path)

        resp = self.session.post(
            f"{self.AJAX_URL}?action=delete",
            data={
                "sesskey": ctx.sesskey,
                "client_id": ctx.client_id,
                "itemid": ctx.itemid,
                "filepath": norm_path,
                "filename": filename,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and "error" in data:
            raise RuntimeError(f"Failed to delete '{filename}': {data['error']}")

        self._commit_draft(ctx)
        return True
