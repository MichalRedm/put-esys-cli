"""
HTTP and networking utility helpers.
"""

import os
import re
from typing import Optional
from urllib.parse import unquote

import requests


def extract_filename_from_response(
    resp: requests.Response, fallback_default: str = "downloaded_file"
) -> str:
    """
    Extract filename from Content-Disposition header (RFC 5987 / RFC 6266)
    or URL path, decoding UTF-8 bytes to prevent Mojibake and sanitizing
    filesystem-invalid characters.
    """
    cd = resp.headers.get("Content-Disposition", "")
    filename: Optional[str] = None

    if cd:
        # Check RFC 5987 filename*=UTF-8''filename.ext
        match_utf8 = re.search(r"filename\*=UTF-8''([^;]+)", cd, re.IGNORECASE)
        if match_utf8:
            filename = unquote(match_utf8.group(1).strip(' "'))
        else:
            match_std = re.search(r'filename="?([^";]+)"?', cd)
            if match_std:
                raw_fn = match_std.group(1).strip()
                try:
                    filename = raw_fn.encode("latin1").decode("utf-8")
                except (UnicodeEncodeError, UnicodeDecodeError):
                    filename = raw_fn

    if not filename:
        clean_url = resp.url.split("?")[0]
        base = os.path.basename(clean_url)
        if base and base != "pluginfile.php":
            filename = unquote(base)
        else:
            parts = clean_url.split("/")
            if len(parts) > 1 and parts[-1] and parts[-1] != "pluginfile.php":
                filename = unquote(parts[-1])

    if not filename or filename == "pluginfile.php":
        filename = fallback_default

    # Replace characters invalid in Windows & POSIX filenames
    filename = re.sub(r'[\\/*?:"<>|]', "_", filename)
    return filename


def download_stream_to_file(
    resp: requests.Response,
    target_path: str,
    chunk_size: int = 32768,
) -> int:
    """
    Writes a streaming requests.Response to target_path on disk.
    Creates parent directories if necessary.
    Returns total bytes written.
    """
    parent_dir = os.path.dirname(target_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    total_bytes = 0
    with open(target_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                total_bytes += len(chunk)
    return total_bytes
