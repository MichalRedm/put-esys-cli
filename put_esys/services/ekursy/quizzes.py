import re
from typing import Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from put_esys.models.quiz import (
    Attachment,
    Question,
    QuizActionButton,
    QuizAttemptDetails,
    QuizAttemptSummary,
    QuizInfo,
)
from put_esys.utils.markdown import markdown_to_html_with_math

from .draft_files import upload_draft_file


class QuizService:
    def __init__(self, session: requests.Session):
        self.session = session

    def get_quiz_info(self, quiz_id: str) -> Tuple[Optional[QuizInfo], Optional[str]]:
        """Show status and attempts for a specific quiz."""
        url = f"https://ekursy.put.poznan.pl/mod/quiz/view.php?id={quiz_id}"
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
        except Exception as e:
            return None, f"Failed to access quiz page: {e}"

        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract sesskey
        sesskey_match = re.search(r'"sesskey":"([^"]+)"', resp.text)
        sesskey = sesskey_match.group(1) if sesskey_match else None
        if not sesskey:
            logout_link = soup.find("a", href=re.compile(r"sesskey=([^&]+)"))
            if logout_link:
                sesskey = re.search(r"sesskey=([^&]+)", logout_link["href"]).group(1)

        title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "Unknown Quiz"

        # Extract intro text
        intro_div = soup.find(id="intro") or soup.select_one(".quizdescription")
        intro = str(intro_div) if intro_div else ""

        # Extract all info paragraphs (Time limit, Grading method, etc.)
        info_paragraphs = [p.get_text(strip=True) for p in soup.select(".quizinfo p")]

        # Also check for availability info
        avail_info = soup.select_one(".availabilityinfo")
        if avail_info:
            info_paragraphs.append(avail_info.get_text(strip=True))

        grading_method = "Unknown"
        for p in info_paragraphs:
            if "Grading method" in p or "Metoda oceniania" in p:
                grading_method = p.split(":")[-1].strip()
                break

        attempts = []
        attempt_cards = soup.select(".generaltable.quizreviewsummary")
        for card in attempt_cards:
            attempt_data = {}
            for row in card.select("tr"):
                th = row.find("th")
                td = row.find("td")
                if th and td:
                    key = th.get_text(strip=True).lower()
                    val = td.get_text(strip=True)
                    attempt_data[key] = val

            header = card.find_previous("h4", class_="card-title")
            if header:
                attempt_data["number"] = header.get_text(strip=True)

            review_link = (
                card.find_parent("div", class_="card").find("a", string="Review")
                if card.find_parent("div", class_="card")
                else None
            )
            if not review_link:
                review_link = card.find_next("a", string="Review")

            if review_link:
                href = review_link.get("href")
                attempt_data["review_url"] = href
                match = re.search(r"attempt=(\d+)", href)
                if match:
                    attempt_data["id"] = match.group(1)

            # If in progress and no ID found, try to find it in the "Continue" button
            if attempt_data.get("status") == "In progress" and not attempt_data.get("id"):
                continue_form = soup.select_one(".quizstartbuttondiv form")
                if continue_form:
                    action = continue_form.get("action")
                    if action:
                        data = {
                            inp.get("name"): inp.get("value")
                            for inp in continue_form.find_all("input")
                        }
                        try:
                            r = self.session.post(action, data=data, allow_redirects=False)
                            loc = r.headers.get("Location", "")
                            match = re.search(r"attempt=(\d+)", loc)
                            if match:
                                attempt_data["id"] = match.group(1)
                        except Exception:
                            pass

            attempts.append(
                QuizAttemptSummary(
                    number=attempt_data.get("number"),
                    id=attempt_data.get("id"),
                    status=attempt_data.get("status") or attempt_data.get("stan"),
                    started=attempt_data.get("started") or attempt_data.get("rozpoczęto"),
                    grade=attempt_data.get("grade") or attempt_data.get("ocena"),
                    review_url=attempt_data.get("review_url"),
                )
            )

        # Check for buttons
        buttons = []
        for form in soup.select(".quizstartbuttondiv form"):
            btn = form.find("button")
            if btn:
                buttons.append(
                    QuizActionButton(text=btn.get_text(strip=True), url=form.get("action"))
                )

        return (
            QuizInfo(
                title=title,
                intro=intro,
                info=info_paragraphs,
                grading_method=grading_method,
                attempts=attempts,
                buttons=buttons,
                sesskey=sesskey,
            ),
            None,
        )

    def start_quiz_attempt(self, quiz_id: str) -> Tuple[Optional[str], Optional[str]]:
        """Start a new quiz attempt."""
        url = f"https://ekursy.put.poznan.pl/mod/quiz/view.php?id={quiz_id}"
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
        except Exception as e:
            return None, f"Failed to access quiz page: {e}"

        soup = BeautifulSoup(resp.text, "html.parser")

        sesskey_match = re.search(r'"sesskey":"([^"]+)"', resp.text)
        sesskey = sesskey_match.group(1) if sesskey_match else None
        if not sesskey:
            logout_link = soup.find("a", href=re.compile(r"sesskey=([^&]+)"))
            if logout_link:
                sesskey = re.search(r"sesskey=([^&]+)", logout_link["href"]).group(1)

        if not sesskey:
            return None, "Could not find session key (sesskey). Page structure might have changed."

        continue_form = soup.select_one(".quizstartbuttondiv form")
        if continue_form:
            btn = continue_form.find("button")
            if btn and (
                "kontynuuj" in btn.get_text().lower() or "continue" in btn.get_text().lower()
            ):
                action = continue_form.get("action")
                data = {
                    inp.get("name"): inp.get("value")
                    for inp in continue_form.find_all("input")
                    if inp.get("name")
                }
                r = self.session.post(action, data=data, allow_redirects=True)
                match = re.search(r"attempt=(\d+)", r.url)
                if match:
                    return match.group(1), None

        start_url = "https://ekursy.put.poznan.pl/mod/quiz/startattempt.php"
        if continue_form and continue_form.get("action"):
            action = continue_form.get("action")
            if action.startswith("http"):
                start_url = action
            else:
                start_url = urljoin(url, action)

        data = {"cmid": quiz_id, "sesskey": sesskey}
        if continue_form:
            for inp in continue_form.find_all("input"):
                if inp.get("name") and inp.get("value"):
                    data[inp.get("name")] = inp.get("value")

        try:
            resp = self.session.post(start_url, data=data, allow_redirects=True)
            resp.raise_for_status()

            match = re.search(r"attempt=(\d+)", resp.url)
            if match:
                return match.group(1), None
            else:
                if "Password" in resp.text:
                    return None, "This quiz requires a password. Please start it in the browser."
                return None, f"Started attempt but could not find attempt ID in URL: {resp.url}"
        except Exception as e:
            return None, f"Failed to start attempt: {e}"

    def get_quiz_attempt(
        self, quiz_id: str, attempt_id: Optional[str]
    ) -> Tuple[Optional[QuizAttemptDetails], Optional[str]]:
        """View questions and answers for a specific quiz attempt."""
        if attempt_id is None:
            info, error = self.get_quiz_info(quiz_id)
            if error:
                return None, error

            in_progress = [a for a in info.attempts if a.status in ["In progress", "W toku"]]
            if in_progress and in_progress[0].id:
                attempt_id = in_progress[0].id
            elif info.attempts and info.attempts[0].id:
                attempt_id = info.attempts[0].id
            else:
                return None, "Could not find any quiz attempts. Start one in the browser first."

        url = (
            f"https://ekursy.put.poznan.pl/mod/quiz/review.php?attempt={attempt_id}&cmid={quiz_id}"
        )
        try:
            resp = self.session.get(url)
            resp.raise_for_status()

            if "mod/quiz/view.php" in resp.url:
                url = (
                    f"https://ekursy.put.poznan.pl/mod/quiz/attempt.php"
                    f"?attempt={attempt_id}&cmid={quiz_id}"
                )
                resp = self.session.get(url)
                resp.raise_for_status()
        except Exception as e:
            return None, f"Failed to access attempt page: {e}"

        soup = BeautifulSoup(resp.text, "html.parser")

        questions = []
        for que_div in soup.select(".que"):
            q_no_el = que_div.select_one(".qno")
            q_no = q_no_el.get_text(strip=True) if q_no_el else "?"

            q_state_el = que_div.select_one(".state")
            q_state = q_state_el.get_text(strip=True) if q_state_el else ""

            q_text_el = que_div.select_one(".qtext")
            q_text_html = str(q_text_el) if q_text_el else ""

            answer_div = que_div.select_one(".qtype_essay_response") or que_div.select_one(
                ".answer"
            )

            textarea = que_div.find("textarea")
            if textarea:
                answer_html = textarea.get_text(strip=True)
            else:
                answer_html = str(answer_div) if answer_div else "No answer found"

            options = []
            for option_div in que_div.select(".answer > div"):
                label = option_div.find("label")
                if label:
                    is_selected = "checked" in str(option_div) or "selected" in str(option_div)
                    options.append({"text": label.get_text(strip=True), "selected": is_selected})

            if options:
                opt_list = []
                for opt in options:
                    marker = "<b>[x]</b>" if opt["selected"] else "[ ]"
                    opt_list.append(f"<li>{marker} {opt['text']}</li>")
                answer_html = f"<ul>{''.join(opt_list)}</ul>"

            attachments = []
            allows_attachments = False
            att_div = que_div.select_one(".attachments")
            if att_div:
                if att_div.find(recursive=False) or att_div.get_text(strip=True):
                    allows_attachments = True

                for att_link in att_div.select("a"):
                    att_name = att_link.get_text(strip=True)
                    att_url = att_link.get("href")
                    if att_name and att_url and not att_url.startswith("#"):
                        attachments.append(Attachment(name=att_name, url=att_url))

                # If in progress and no attachments found via simple links, try draftfiles_manager
                att_input = que_div.find("input", attrs={"name": re.compile(r"_attachments$")})
                if att_input:
                    allows_attachments = True
                    itemid = att_input.get("value")
                    ctx_match = re.search(r'"contextid":(\d+)', resp.text)
                    ctx_id = ctx_match.group(1) if ctx_match else None
                    sesskey_match = re.search(r'"sesskey":"([^"]+)"', resp.text)
                    sesskey = sesskey_match.group(1) if sesskey_match else None

                    if itemid and ctx_id and sesskey:
                        draft_url = (
                            f"https://ekursy.put.poznan.pl/repository/draftfiles_manager.php"
                            f"?env=filemanager&action=browse&itemid={itemid}"
                            f"&ctx_id={ctx_id}&sesskey={sesskey}"
                        )
                        try:
                            draft_r = self.session.get(draft_url)
                            draft_soup = BeautifulSoup(draft_r.text, "html.parser")
                            for link in draft_soup.select("a"):
                                href = link.get("href", "")
                                text = link.get_text(strip=True)
                                if "/draftfile.php/" in href and text and not link.get("class"):
                                    if not any(a.name == text for a in attachments):
                                        attachments.append(Attachment(name=text, url=href))
                        except Exception:
                            pass

            q_type = "unknown"
            for cls in que_div.get("class", []):
                is_qtype = cls.startswith("qtype_")
                is_known = cls in ["essay", "multichoice", "truefalse", "shortanswer"]
                if is_qtype or is_known:
                    q_type = cls.replace("qtype_", "")
                    break

            # Parse teacher comment
            comment_html = None
            comment_el = que_div.select_one(".comment")
            if comment_el:
                no_overflow = comment_el.select_one(".no-overflow")
                if no_overflow:
                    comment_html = str(no_overflow)
                else:
                    h4_el = comment_el.find("h4")
                    h4_text = h4_el.get_text(strip=True) if h4_el else ""
                    full_text = comment_el.get_text(strip=True)
                    if h4_text and full_text.startswith(h4_text):
                        text = full_text[len(h4_text):].strip()
                    else:
                        text = full_text.strip()
                    text = re.sub(r'^(comment|komentarz):\s*', '', text, flags=re.IGNORECASE)
                    if text:
                        comment_html = f"<p>{text}</p>"

            questions.append(
                Question(
                    number=q_no,
                    state=q_state,
                    type=q_type,
                    allows_attachments=allows_attachments,
                    text=q_text_html,
                    answer=answer_html,
                    attachments=attachments,
                    comment=comment_html,
                )
            )

        return (
            QuizAttemptDetails(
                quiz_id=int(quiz_id), attempt_id=int(attempt_id), questions=questions
            ),
            None,
        )

    def save_quiz_answer(
        self,
        quiz_id: str,
        attempt_id: str,
        question_number: int,
        new_text: Optional[str] = None,
        attachment_path: Optional[str] = None,
        remove_attachment: Optional[str] = None,
        new_name: Optional[str] = None,
        rename_attachment: Optional[str] = None,
    ) -> bool:
        """Save an answer for a specific question in an in-progress attempt."""
        url = (
            f"https://ekursy.put.poznan.pl/mod/quiz/attempt.php?attempt={attempt_id}&cmid={quiz_id}"
        )
        r = self.session.get(url)
        soup = BeautifulSoup(r.text, "html.parser")

        form = soup.select_one("#responseform")
        if not form:
            raise Exception("Could not find the quiz form. Is the attempt in progress?")

        data = {}
        for inp in form.find_all(["input", "textarea"]):
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

        target_name = None
        itemid = None
        for que_div in soup.select(".que"):
            q_no_el = que_div.select_one(".qno")
            if q_no_el and q_no_el.get_text(strip=True) == str(question_number):
                textarea = que_div.select_one("textarea")
                if textarea:
                    target_name = textarea.get("name")

                att_input = que_div.find("input", attrs={"name": re.compile(r"_attachments$")})
                if att_input:
                    itemid = att_input.get("value")
                break

        ctx_match = re.search(r'"contextid":(\d+)', r.text)
        ctx_id = ctx_match.group(1) if ctx_match else None

        if attachment_path:
            if not itemid:
                raise Exception(f"Question {question_number} does not support file attachments.")
            if not ctx_id:
                raise Exception("Could not find context ID on the quiz page.")
            sesskey = data.get("sesskey")
            if not sesskey:
                raise Exception("Could not find session key (sesskey).")
            upload_draft_file(self.session, attachment_path, itemid, ctx_id, sesskey, new_name)

        if remove_attachment:
            if not itemid:
                raise Exception(f"Question {question_number} does not support file attachments.")
            if not ctx_id:
                raise Exception("Could not find context ID on the quiz page.")
            sesskey = data.get("sesskey")
            if not sesskey:
                raise Exception("Could not find session key (sesskey).")

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
                raise Exception("New name (--new-name) must be provided to rename an attachment.")
            if not itemid:
                raise Exception(f"Question {question_number} does not support file attachments.")
            if not ctx_id:
                raise Exception("Could not find context ID on the quiz page.")
            sesskey = data.get("sesskey")
            if not sesskey:
                raise Exception("Could not find session key (sesskey).")

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
            post_data = {"newfilename": new_name, "filename": rename_attachment, "draftpath": "/"}
            resp = self.session.post(rename_url, params=params, data=post_data)
            resp.raise_for_status()
            if "errormessage" in resp.text or "errorcode" in resp.text:
                raise Exception(f"File renaming failed: {resp.text}")

        if new_text is not None:
            if not target_name:
                raise Exception(f"Could not find input for question {question_number}")

            format_name = f"{target_name}format"
            if data.get(format_name) == "1":
                # Render using the extracted utilities parser
                data[target_name] = markdown_to_html_with_math(new_text)
            else:
                data[target_name] = new_text

        data["next"] = "1"
        post_url = form.get("action")
        if not post_url.startswith("http"):
            post_url = urljoin(url, post_url)

        r = self.session.post(post_url, data=data)
        r.raise_for_status()
        return True

    def submit_quiz_attempt(self, quiz_id: str, attempt_id: str) -> Tuple[bool, Optional[str]]:
        """Submit a quiz attempt to finalize and grade it."""
        url = (
            f"https://ekursy.put.poznan.pl/mod/quiz/summary.php?attempt={attempt_id}&cmid={quiz_id}"
        )
        resp = self.session.get(url)
        resp.raise_for_status()

        if (
            "mod/quiz/review.php" in resp.url
            or "zakończone" in resp.text.lower()
            or "złożone" in resp.text.lower()
            or "finished" in resp.text.lower()
            or "submitted" in resp.text.lower()
        ):
            return True, "Attempt is already submitted or finished."

        soup = BeautifulSoup(resp.text, "html.parser")
        form = soup.find("form", id="frm-finishattempt") or soup.find(
            "form", action=re.compile(r"processattempt\.php")
        )

        if not form:
            return False, "Could not find the quiz submission form on the summary page."

        post_url = form.get("action")
        if not post_url.startswith("http"):
            post_url = urljoin(url, post_url)

        data = {}
        for inp in form.find_all(["input", "button"]):
            name = inp.get("name")
            if name:
                data[name] = inp.get("value", "")

        data["finishattempt"] = "1"

        post_resp = self.session.post(post_url, data=data)
        post_resp.raise_for_status()

        if "review.php" in post_resp.url:
            return True, None

        info, error = self.get_quiz_info(quiz_id)
        if not error and info.attempts:
            for att in info.attempts:
                if att.id == str(attempt_id):
                    if att.status in ["Finished", "Submitted", "Zakończone", "Odesłane"]:
                        return True, None
                    else:
                        return False, f"Attempt status is still: {att.status}"

        if "view.php" in post_resp.url or "review.php" in post_resp.url:
            return True, None

        return False, "Could not confirm successful submission from the redirection URL."
