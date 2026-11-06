"""
Course enrolment inspection and self-enrolment services.
"""

import re
from typing import Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from put_esys.models.course import EnrolmentInfo, EnrolmentStatus


class CourseEnrolmentService:
    """Handles inspecting enrolment options and submitting self-enrolment forms."""

    def __init__(self, session: requests.Session):
        self.session = session

    def get_enrolment_info(
        self, course_id: str
    ) -> Tuple[Optional[EnrolmentInfo], Optional[str]]:
        """Inspect course enrolment options and prerequisites."""
        url = f"https://ekursy.put.poznan.pl/course/view.php?id={course_id}"
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            return None, f"Failed to access course page: {e}"

        soup = BeautifulSoup(resp.text, "html.parser")
        if "course/view.php" in resp.url:
            h1 = soup.find("h1")
            course_title = h1.get_text(strip=True) if h1 else f"Course {course_id}"
            return EnrolmentInfo(
                course_id=course_id,
                course_title=course_title,
                status=EnrolmentStatus.ALREADY_ENROLLED,
            ), None

        soup = BeautifulSoup(resp.text, "html.parser")
        main_region = soup.select_one("#region-main") or soup.find("div", role="main") or soup

        coursename_el = main_region.select_one("h3.coursename") or main_region.select_one(
            ".coursename"
        )
        if coursename_el:
            course_title = coursename_el.get_text(strip=True)
        else:
            title_tag = (
                main_region.select_one("h1")
                or main_region.select_one("h2")
                or soup.select_one("h1")
                or soup.title
            )
            course_title = title_tag.get_text(strip=True) if title_tag else f"Course {course_id}"
            if " | eKursy" in course_title:
                course_title = course_title.split(" | eKursy")[0].strip()

        enrol_form = None
        for form in main_region.find_all("form"):
            if (
                "enrol" in form.get("action", "")
                or form.find("input", {"name": "enrolpassword"})
                or form.find("input", {"name": "instance"})
            ):
                enrol_form = form
                break

        if not enrol_form:
            page_text = main_region.get_text()
            if (
                "You cannot enrol yourself in this course" in page_text
                or "Nie możesz zapisać się na ten kurs" in page_text
            ):
                return EnrolmentInfo(
                    course_id=course_id,
                    course_title=course_title,
                    status=EnrolmentStatus.NO_SELF_ENROLMENT,
                    error_message=(
                        "Self-enrolment is disabled for this course. "
                        "Please contact the instructor."
                    ),
                ), None

            return EnrolmentInfo(
                course_id=course_id,
                course_title=course_title,
                status=EnrolmentStatus.NO_SELF_ENROLMENT,
                error_message="No self-enrolment form found on page.",
            ), None

        instance_tag = enrol_form.find("input", {"name": "instance"})
        instance_id = instance_tag.get("value") if instance_tag else None

        sesskey_tag = enrol_form.find("input", {"name": "sesskey"})
        sesskey = sesskey_tag.get("value") if sesskey_tag else None
        if not sesskey:
            sesskey_match = re.search(r'"sesskey":"([^"]+)"', resp.text)
            if sesskey_match:
                sesskey = sesskey_match.group(1)

        password_input = enrol_form.find("input", {"name": "enrolpassword"})
        requires_password = password_input is not None

        status = (
            EnrolmentStatus.CAN_ENROL_KEY_REQUIRED
            if requires_password
            else EnrolmentStatus.CAN_ENROL
        )

        return EnrolmentInfo(
            course_id=course_id,
            course_title=course_title,
            status=status,
            requires_password=requires_password,
            instance_id=instance_id,
            sesskey=sesskey,
        ), None

    def enrol_course(
        self, course_id: str, password: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """Submit self-enrolment into a course with optional enrolment key."""
        url = f"https://ekursy.put.poznan.pl/course/view.php?id={course_id}"
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            return False, f"Failed to access course page: {e}"

        if "course/view.php" in resp.url:
            return True, "Already enrolled in this course."

        soup = BeautifulSoup(resp.text, "html.parser")
        main_region = soup.select_one("#region-main") or soup.find("div", role="main") or soup

        enrol_form = None
        for form in main_region.find_all("form"):
            if (
                "enrol" in form.get("action", "")
                or form.find("input", {"name": "enrolpassword"})
                or form.find("input", {"name": "instance"})
            ):
                enrol_form = form
                break

        if not enrol_form:
            page_text = main_region.get_text()
            if (
                "You cannot enrol yourself in this course" in page_text
                or "Nie możesz zapisać się na ten kurs" in page_text
            ):
                return False, (
                    "Self-enrolment is disabled for this course. "
                    "Please contact the instructor."
                )
            return False, "No self-enrolment form found on page."

        form_data = {}
        for inp in enrol_form.find_all("input"):
            name = inp.get("name")
            if not name:
                continue
            val = inp.get("value", "")
            form_data[name] = val

        form_data["id"] = course_id
        if "sesskey" not in form_data or not form_data["sesskey"]:
            sesskey_match = re.search(r'"sesskey":"([^"]+)"', resp.text)
            if sesskey_match:
                form_data["sesskey"] = sesskey_match.group(1)

        requires_password = enrol_form.find("input", {"name": "enrolpassword"}) is not None
        if requires_password:
            if not password:
                return False, "This course requires an enrolment key. Provide it via --key."
            form_data["enrolpassword"] = password

        submit_btn = enrol_form.find("input", {"type": "submit"}) or enrol_form.find(
            "button", {"type": "submit"}
        )
        if submit_btn and submit_btn.get("name"):
            form_data[submit_btn["name"]] = submit_btn.get("value", "Zapisz mnie")
        elif "submitbutton" not in form_data:
            form_data["submitbutton"] = "Zapisz mnie"

        action = enrol_form.get("action", "")
        post_url = urljoin(resp.url, action) if action else url

        try:
            post_resp = self.session.post(
                post_url, data=form_data, headers={"Referer": resp.url}, timeout=30
            )
            post_resp.raise_for_status()
        except Exception as e:
            return False, f"Failed to submit enrolment form: {e}"

        if "course/view.php" in post_resp.url:
            return True, "Successfully enrolled in course!"

        post_soup = BeautifulSoup(post_resp.text, "html.parser")
        error_el = (
            post_soup.select_one(".alert-danger")
            or post_soup.select_one("span.error")
            or post_soup.select_one(".error")
        )
        if error_el:
            err_text = error_el.get_text(strip=True)
            return False, f"Enrolment failed: {err_text}"

        if "enrolpassword" in post_resp.text and requires_password:
            return False, "Enrolment failed: Incorrect enrolment key."

        return False, "Enrolment could not be confirmed. Check course status manually."
