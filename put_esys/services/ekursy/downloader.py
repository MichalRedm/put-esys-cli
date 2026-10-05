"""
Course resource downloading and file categorization service.
"""

import os
from typing import List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from put_esys.models.course import CourseContent, DownloadedResource
from put_esys.utils.http import download_stream_to_file, extract_filename_from_response


class CourseDownloaderService:
    """Handles downloading course activities (files, folders) and local folder structuring."""

    def __init__(self, session: requests.Session):
        self.session = session

    def _download_single_file(self, url: str, target_dir: str) -> Optional[Tuple[str, int]]:
        """Download a single file from URL into target_dir."""
        try:
            resp = self.session.get(url, stream=True, timeout=60)
            resp.raise_for_status()
        except Exception:
            return None

        # Check for HTML redirect or lock
        content_type = resp.headers.get("Content-Type", "")
        if "text/html" in content_type and "course/view.php" in resp.url:
            return None

        filename = extract_filename_from_response(resp)
        dest_path = os.path.join(target_dir, filename)
        total_bytes = download_stream_to_file(resp, dest_path)

        return filename, total_bytes

    def download_resources(
        self,
        content: CourseContent,
        output_dir: str,
        section_filter: Optional[str] = None,
        flat: bool = False,
    ) -> List[DownloadedResource]:
        """
        Downloads all downloadable activities (files and folders) from parsed course content.
        Categorizes files into subfolders (lecture, lab, project, general) unless flat=True.
        """
        downloaded_resources: List[DownloadedResource] = []

        for section in content.sections:
            if section_filter and section_filter.lower() not in section.name.lower():
                continue

            sec_lower = section.name.lower()
            if flat:
                target_subfolder = output_dir
            elif "lab" in sec_lower or "task" in sec_lower or "zadani" in sec_lower:
                target_subfolder = os.path.join(output_dir, "lab")
            elif "project" in sec_lower or "proj" in sec_lower:
                target_subfolder = os.path.join(output_dir, "project")
            elif "lecture" in sec_lower or "wykład" in sec_lower:
                target_subfolder = os.path.join(output_dir, "lecture")
            elif "seminar" in sec_lower or "seminarium" in sec_lower:
                target_subfolder = os.path.join(output_dir, "seminar")
            elif "class" in sec_lower or "ćwiczen" in sec_lower:
                target_subfolder = os.path.join(output_dir, "classes")
            else:
                target_subfolder = os.path.join(output_dir, "lecture")

            for act in section.activities:
                if act.is_restricted or not act.url:
                    continue

                if act.type in ("resource", "folder") or act.children:
                    # Case 1: Folder module
                    if act.type == "folder" or "mod/folder/view.php" in act.url:
                        try:
                            f_resp = self.session.get(act.url, timeout=30)
                            f_soup = BeautifulSoup(f_resp.text, "html.parser")
                            f_links = [
                                a["href"]
                                for a in f_soup.find_all("a", href=True)
                                if "pluginfile.php" in a["href"]
                            ]
                            for fl in f_links:
                                res = self._download_single_file(fl, target_subfolder)
                                if res:
                                    fn, sz = res
                                    downloaded_resources.append(
                                        DownloadedResource(
                                            name=fn,
                                            path=os.path.join(target_subfolder, fn),
                                            size_bytes=sz,
                                            section=section.name,
                                            activity_type=act.type,
                                        )
                                    )
                        except Exception:
                            continue

                    # Case 2: Resource landing page or direct resource
                    elif act.type == "resource" or "mod/resource/view.php" in act.url:
                        try:
                            r_resp = self.session.get(act.url, timeout=30)
                            c_type = r_resp.headers.get("Content-Type", "")
                            if "text/html" in c_type:
                                r_soup = BeautifulSoup(r_resp.text, "html.parser")
                                plugin_links = [
                                    a["href"]
                                    for a in r_soup.find_all("a", href=True)
                                    if "pluginfile.php" in a["href"]
                                ]
                                if plugin_links:
                                    res = self._download_single_file(
                                        plugin_links[0], target_subfolder
                                    )
                                    if res:
                                        fn, sz = res
                                        downloaded_resources.append(
                                            DownloadedResource(
                                                name=fn,
                                                path=os.path.join(target_subfolder, fn),
                                                size_bytes=sz,
                                                section=section.name,
                                                activity_type=act.type,
                                            )
                                        )
                            else:
                                res = self._download_single_file(act.url, target_subfolder)
                                if res:
                                    fn, sz = res
                                    downloaded_resources.append(
                                        DownloadedResource(
                                            name=fn,
                                            path=os.path.join(target_subfolder, fn),
                                            size_bytes=sz,
                                            section=section.name,
                                            activity_type=act.type,
                                        )
                                    )
                        except Exception:
                            continue

                    # Case 3: Children activities embedded
                    if act.children:
                        for ch in act.children:
                            if ch.url:
                                res = self._download_single_file(ch.url, target_subfolder)
                                if res:
                                    fn, sz = res
                                    downloaded_resources.append(
                                        DownloadedResource(
                                            name=fn,
                                            path=os.path.join(target_subfolder, fn),
                                            size_bytes=sz,
                                            section=section.name,
                                            activity_type=ch.type,
                                        )
                                    )

        return downloaded_resources
