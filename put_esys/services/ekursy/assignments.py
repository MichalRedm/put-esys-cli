import os
import re
from typing import Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from put_esys.models.assignment import AssignmentInfo, AssignmentRow, SubmittedFile

from .draft_files import upload_draft_file


class AssignmentService:
    def __init__(self, session: requests.Session):
        self.session = session

    def get_assignment_info(self, assign_id: str) -> Tuple[Optional[AssignmentInfo], Optional[str]]:
        """Show content and status of a specific assignment."""
        url = f"https://ekursy.put.poznan.pl/mod/assign/view.php?id={assign_id}"
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
        except Exception as e:
            return None, f"Failed to access assignment page: {e}"

        soup = BeautifulSoup(resp.text, "html.parser")

        # Follow non-JS comments link if present to get static comment list
        nonjs_link = soup.select_one("a.showcommentsnonjs")
        if nonjs_link and nonjs_link.get("href"):
            try:
                nonjs_url = urljoin(url, nonjs_link["href"])
                comment_resp = self.session.get(nonjs_url)
                comment_resp.raise_for_status()
                soup = BeautifulSoup(comment_resp.text, "html.parser")
            except Exception:
                pass

        title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "Unknown Assignment"

        # Extract description
        intro_div = (
            soup.find(id="intro")
            or soup.select_one(".box.generalbox")
            or soup.select_one(".assignmentdescription")
            or soup.select_one(".activity-description")
        )
        intro = str(intro_div) if intro_div else ""

        # Extract tables
        tables_data = []
        for table in soup.select("table.generaltable"):
            table_rows = []
            for row in table.select("tr"):
                th = row.find("th")
                td = row.find("td")
                if th and td:
                    key = th.get_text(strip=True)

                    # Custom parser for comments container to avoid ugly templates
                    comments_container = td.select_one(".commentscontainer")
                    if comments_container:
                        comments = []
                        for li in comments_container.select(".comment-list li"):
                            text_el = li.select_one(".text")
                            user_el = li.select_one(".user")
                            time_el = li.select_one(".time")

                            if text_el:
                                user = user_el.get_text(strip=True) if user_el else "Unknown"
                                time_str = (
                                    time_el.get_text(strip=True).strip("- ")
                                    if time_el
                                    else "Unknown"
                                )
                                text = text_el.get_text(strip=True)
                                comments.append(f"• {user} ({time_str}): {text}")
                        if comments:
                            val = "\n".join(comments)
                        else:
                            count_el = comments_container.select_one(".comment-link")
                            val = count_el.get_text(strip=True) if count_el else "No comments"
                    else:
                        val = td.get_text(strip=True)

                    # Check for attachments inside this td
                    files = []
                    for a in td.select("a"):
                        href = a.get("href", "")
                        if "pluginfile.php" in href or "draftfile.php" in href:
                            files.append(SubmittedFile(name=a.get_text(strip=True), url=href))

                    table_rows.append(AssignmentRow(key=key, value=val, files=files))
            if table_rows:
                tables_data.append(table_rows)

        return AssignmentInfo(id=assign_id, title=title, intro=intro, tables=tables_data), None

    def save_assignment_submission(
        self,
        assign_id: str,
        file_path: Optional[str] = None,
        new_name: Optional[str] = None,
        new_text: Optional[str] = None,
        text_file: Optional[str] = None,
        remove_attachment: Optional[str] = None,
        rename_attachment: Optional[str] = None,
    ) -> bool:
        """Save changes to an assignment submission (draft files and online text)."""
        url = (
            f"https://ekursy.put.poznan.pl/mod/assign/view.php?id={assign_id}&action=editsubmission"
        )
        r = self.session.get(url)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Find the submission form
        form = None
        for f in soup.select("form"):
            action_attr = f.get("action", "")
            method_attr = f.get("method", "").lower()
            if "mod/assign/view.php" in action_attr and method_attr == "post":
                if f.find("input", attrs={"name": "action", "value": "savesubmission"}):
                    form = f
                    break

        if not form:
            raise Exception(
                "Could not find the assignment submission form. "
                "Is the assignment closed or already submitted?"
            )

        data = {}
        for inp in form.find_all(["input", "textarea", "select"]):
            name = inp.get("name")
            if not name:
                continue

            if inp.name == "textarea":
                data[name] = inp.get_text()
            elif inp.get("type") == "checkbox":
                if inp.has_attr("checked"):
                    data[name] = inp.get("value", "1")
            elif inp.get("type") == "radio":
                if inp.has_attr("checked"):
                    data[name] = inp.get("value")
            else:
                data[name] = inp.get("value", "")

        data.pop("cancel", None)

        # Find online text field name if any
        onlinetext_name = None
        for key in data:
            if "onlinetext_editor" in key and key.endswith("[text]"):
                onlinetext_name = key
                break

        # Read text from file if provided
        if text_file:
            if not os.path.exists(text_file):
                raise FileNotFoundError(f"Text file not found: {text_file}")
            with open(text_file, "r", encoding="utf-8") as f:
                new_text = f.read()

        # Update online text if provided
        if new_text is not None:
            if not onlinetext_name:
                for textarea in form.find_all("textarea"):
                    t_name = textarea.get("name", "")
                    if "onlinetext" in t_name:
                        onlinetext_name = t_name
                        break
            if not onlinetext_name:
                raise Exception("This assignment does not support online text submissions.")
            data[onlinetext_name] = new_text

        # Extract files_filemanager itemid
        itemid = data.get("files_filemanager")

        # Extract context ID
        ctx_match = re.search(r'"contextid":(\d+)', r.text)
        ctx_id = ctx_match.group(1) if ctx_match else None

        # Handle attachments
        if file_path or remove_attachment or rename_attachment:
            if not itemid:
                raise Exception("This assignment does not support file submissions.")

            if not ctx_id:
                raise Exception("Could not find context ID on the assignment page.")

            sesskey = data.get("sesskey")
            if not sesskey:
                raise Exception("Could not find session key (sesskey) in the form.")

            if file_path:
                upload_draft_file(self.session, file_path, itemid, ctx_id, sesskey, new_name)

            if remove_attachment:
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
                    "filename": remove_attachment,
                }
                resp = self.session.get(delete_url, params=params)
                resp.raise_for_status()

            if rename_attachment:
                if not new_name:
                    raise Exception("New name must be provided to rename an attachment.")
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
                post_data = {
                    "newfilename": new_name,
                    "filename": rename_attachment,
                    "draftpath": "/",
                }
                resp = self.session.post(rename_url, params=params, data=post_data)
                resp.raise_for_status()
                if "errormessage" in resp.text or "errorcode" in resp.text:
                    raise Exception(f"File renaming failed: {resp.text}")

        # Submit the form data
        post_url = form.get("action")
        if not post_url.startswith("http"):
            post_url = urljoin(url, post_url)

        # Trigger submit button name
        data["submitbutton"] = "Zapisz zmiany"

        post_resp = self.session.post(post_url, data=data)
        post_resp.raise_for_status()

        # Verify redirection or response content
        if "action=editsubmission" in post_resp.url:
            err_soup = BeautifulSoup(post_resp.text, "html.parser")
            err_msg = err_soup.select_one(".error")
            if err_msg:
                raise Exception(f"Failed to save assignment: {err_msg.get_text(strip=True)}")
            raise Exception("Failed to save assignment: redirected back to edit page.")

        return True

    def delete_assignment_submission(self, assign_id: str) -> bool:
        """Delete/remove the assignment submission."""
        url = f"https://ekursy.put.poznan.pl/mod/assign/view.php?id={assign_id}&action=removesubmissionconfirm"
        r = self.session.get(url)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Find the removesubmission form
        form = None
        for f in soup.select("form"):
            action_attr = f.get("action", "")
            method_attr = f.get("method", "").lower()
            if "mod/assign/view.php" in action_attr and method_attr == "post":
                if f.find("input", attrs={"name": "action", "value": "removesubmission"}):
                    form = f
                    break

        if not form:
            raise Exception(
                "Could not find the assignment removal form on the confirmation page. "
                "Is the assignment already empty, or is deletion not allowed?"
            )

        # Extract form inputs
        data = {}
        for inp in form.find_all(["input", "button"]):
            name = inp.get("name")
            if name:
                data[name] = inp.get("value", "")

        post_url = form.get("action")
        if not post_url.startswith("http"):
            post_url = urljoin(url, post_url)

        # POST to delete
        post_resp = self.session.post(post_url, data=data)
        post_resp.raise_for_status()
        return True

    def submit_assignment_submission(self, assign_id: str) -> Tuple[bool, Optional[str]]:
        """Finalize and submit the assignment submission."""
        url = f"https://ekursy.put.poznan.pl/mod/assign/view.php?id={assign_id}"
        r = self.session.get(url)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        submit_form = None
        for f in soup.select("form"):
            if f.find("input", attrs={"name": "action", "value": "submit"}):
                submit_form = f
                break

        if not submit_form:
            return (
                True,
                "No final submission button found (it might be already submitted or not required).",
            )

        # Post to the submit form to load confirmation page
        post_data = {}
        for inp in submit_form.find_all(["input", "button"]):
            name = inp.get("name")
            if name:
                post_data[name] = inp.get("value", "")

        post_url = submit_form.get("action")
        if not post_url.startswith("http"):
            post_url = urljoin(url, post_url)

        confirm_resp = self.session.post(post_url, data=post_data)
        confirm_resp.raise_for_status()

        # Parse confirmation page and submit
        conf_soup = BeautifulSoup(confirm_resp.text, "html.parser")
        conf_form = None
        for f in conf_soup.select("form"):
            if f.find("input", attrs={"name": "id", "value": str(assign_id)}):
                conf_form = f
                break

        if not conf_form:
            conf_form = conf_soup.select_one(".singlebutton form") or conf_soup.select_one("form")

        if not conf_form:
            return False, "Could not find confirmation form on the confirmation page."

        conf_data = {}
        for inp in conf_form.find_all(["input", "button"]):
            name = inp.get("name")
            if name:
                if inp.get("type") == "checkbox":
                    conf_data[name] = "1"
                else:
                    conf_data[name] = inp.get("value", "")

        # Check the submission statement if Moodle requires it
        if conf_form.find("input", attrs={"name": "submissionstatement"}):
            conf_data["submissionstatement"] = "1"

        conf_url = conf_form.get("action")
        if not conf_url.startswith("http"):
            conf_url = urljoin(url, conf_url)

        final_resp = self.session.post(conf_url, data=conf_data)
        final_resp.raise_for_status()

        return True, None
