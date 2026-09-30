import re
from typing import List, Optional, Tuple
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

from put_esys.models.course import (
    Activity,
    CategoryBrowseResult,
    Course,
    CourseCategory,
    CourseContent,
    DiscoveredCourse,
    EnrolmentInfo,
    EnrolmentStatus,
    Section,
)


class CourseService:
    def __init__(self, session: requests.Session):
        self.session = session

    def get_courses(self) -> Tuple[Optional[List[Course]], Optional[str]]:
        """List enrolled courses from eKursy."""
        # 1. Get dashboard to find user ID
        try:
            resp = self.session.get("https://ekursy.put.poznan.pl/")
            resp.raise_for_status()
        except Exception as e:
            return None, f"Failed to access eKursy dashboard: {e}"

        if "Logowanie" in resp.text and "login" in resp.url:
            return None, "Session expired. Please login again."

        # Look for userId in script tags or common locations
        user_id_match = re.search(r'"userId":(\d+)', resp.text)
        if not user_id_match:
            soup = BeautifulSoup(resp.text, "html.parser")
            profile_link = soup.find("a", href=re.compile(r"user/profile.php\?id=(\d+)"))
            if profile_link:
                user_id = re.search(r"id=(\d+)", profile_link["href"]).group(1)
            else:
                in_dashboard = "Kokpit" in resp.text or "Dashboard" in resp.text
                if "login/logout.php" not in resp.text and not in_dashboard:
                    msg = "Could not find user session in eKursy (Dashboard). Try logging in again."
                    return None, msg
                msg = (
                    "Could not identify User ID from dashboard. "
                    "The page structure might have changed."
                )
                return None, msg
        else:
            user_id = user_id_match.group(1)

        # 2. Navigate to Profile page with all courses shown
        profile_url = f"https://ekursy.put.poznan.pl/user/profile.php?id={user_id}&showallcourses=1"
        try:
            resp = self.session.get(profile_url)
            resp.raise_for_status()
        except Exception as e:
            return None, f"Failed to access eKursy profile: {e}"

        soup = BeautifulSoup(resp.text, "html.parser")
        courses = []

        # Strategy A: Look for user/view.php profile-style links
        profile_links = soup.find_all("a", href=re.compile(r"user/view\.php\?.*course=(\d+)"))
        for link in profile_links:
            href = link["href"]
            cid_match = re.search(r"course=(\d+)", href)
            if cid_match:
                cid = cid_match.group(1)
                title = link.get_text(strip=True)
                existing_ids = [c.id for c in courses]
                is_valid_title = title and title not in ["Zobacz więcej", "View", "Kurs"]
                if is_valid_title and cid not in existing_ids:
                    courses.append(
                        Course(
                            id=cid,
                            title=title,
                            url=f"https://ekursy.put.poznan.pl/course/view.php?id={cid}",
                        )
                    )

        # Strategy B: Direct course links (course/view.php?id=COURSE_ID)
        direct_links = soup.find_all("a", href=re.compile(r"course/view\.php\?.*id=(\d+)"))
        for link in direct_links:
            href = link["href"]
            cid_match = re.search(r"id=(\d+)", href)
            if cid_match:
                cid = cid_match.group(1)
                title = link.get_text(strip=True)
                existing_ids = [c.id for c in courses]
                is_valid_title = title and title not in ["Zobacz więcej", "View", "Kurs"]
                if is_valid_title and cid not in existing_ids:
                    courses.append(
                        Course(
                            id=cid,
                            title=title,
                            url=f"https://ekursy.put.poznan.pl/course/view.php?id={cid}",
                        )
                    )

        # Strategy C: Navigation menu (Dashboard fallback)
        if not courses:
            try:
                dashboard_resp = self.session.get("https://ekursy.put.poznan.pl/")
                dashboard_soup = BeautifulSoup(dashboard_resp.text, "html.parser")
                nav_links = dashboard_soup.find_all(
                    "a", href=re.compile(r"course/view.php\?id=(\d+)")
                )
                for link in nav_links:
                    href = link["href"]
                    cid_match = re.search(r"id=(\d+)", href)
                    if cid_match:
                        cid = cid_match.group(1)
                        title = link.get_text(strip=True)
                        if title and len(title) > 3 and cid not in [c.id for c in courses]:
                            courses.append(
                                Course(
                                    id=cid,
                                    title=title,
                                    url=f"https://ekursy.put.poznan.pl/course/view.php?id={cid}",
                                )
                            )
            except Exception:
                pass

        return courses, None

    def get_course_content(self, course_id: str) -> Tuple[Optional[CourseContent], Optional[str]]:
        """Show content of a specific course."""
        url = f"https://ekursy.put.poznan.pl/course/view.php?id={course_id}"
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            return None, f"Failed to access course page: {e}"

        if "enrol/index.php" in resp.url:
            info, _ = self.get_enrolment_info(course_id)
            if info and info.status == EnrolmentStatus.CAN_ENROL_KEY_REQUIRED:
                return None, (
                    f"You are not enrolled in course '{info.course_title}' (ID: {course_id}). "
                    f"Self-enrolment is available (enrolment key required). "
                    f"Run 'put-esys course enrol {course_id} --key <KEY>' to enrol."
                )
            elif info and info.status == EnrolmentStatus.CAN_ENROL:
                return None, (
                    f"You are not enrolled in course '{info.course_title}' (ID: {course_id}). "
                    f"Self-enrolment is open. "
                    f"Run 'put-esys course enrol {course_id}' to enrol."
                )
            else:
                return None, (
                    f"You are not enrolled in course (ID: {course_id}) "
                    "and self-enrolment is disabled. "
                    "Please contact the course instructor for access."
                )


        soup = BeautifulSoup(resp.text, "html.parser")
        course_title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "Unknown Course"


        sections = []
        for section_li in soup.select("li.section"):
            name_tag = section_li.select_one("h3.sectionname") or section_li.select_one(
                ".section-title"
            )

            if name_tag:
                for badge in name_tag.select(".sectionbadges"):
                    badge.decompose()
                for span in name_tag.select(".accesshide"):
                    span.decompose()
                section_name = name_tag.get_text(strip=True)
            else:
                section_id = section_li.get("id", "?")
                section_name = f"Section {section_id}"

            activities = []
            for activity_li in section_li.select("li.activity"):
                a_tag = activity_li.select_one("div.activityname a")
                name = None
                link = None
                activity_type = "unknown"

                for cls in activity_li.get("class", []):
                    if cls.startswith("modtype_"):
                        activity_type = cls.replace("modtype_", "")
                        break

                desc_el = (
                    activity_li.select_one(".activity-altcontent")
                    or activity_li.select_one(".activity-description")
                    or activity_li.select_one(".contentafterlink")
                )
                content_html = str(desc_el) if desc_el else None

                if a_tag:
                    for span in a_tag.find_all("span", class_="accesshide"):
                        span.decompose()
                    name = a_tag.get_text(strip=True)
                    link = a_tag["href"]
                    activities.append(
                        Activity(name=name, url=link, type=activity_type, content=content_html)
                    )
                else:
                    activity_item = activity_li.select_one("div.activity-item")
                    if activity_item and activity_item.has_attr("data-activityname"):
                        activity_base_name = activity_item["data-activityname"]
                        mod_id = activity_li.get("data-id")
                        if mod_id and activity_type != "unknown":
                            link = f"https://ekursy.put.poznan.pl/mod/{activity_type}/view.php?id={mod_id}"
                        else:
                            mod_anchor = f"#module-{activity_li.get('id', '')}"
                            link = f"https://ekursy.put.poznan.pl/course/view.php?id={course_id}{mod_anchor}"

                        fp_links = activity_li.select(".fp-filename a")
                        if fp_links:
                            children = []
                            for fp_link in fp_links:
                                children.append(
                                    Activity(
                                        name=fp_link.get_text(strip=True),
                                        url=fp_link["href"],
                                        type="resource",
                                    )
                                )
                            activities.append(
                                Activity(
                                    name=activity_base_name,
                                    url=link,
                                    type=activity_type,
                                    children=children,
                                    content=content_html,
                                )
                            )
                        else:
                            link_tag = activity_item.select_one(
                                "a.stretched-link"
                            ) or activity_item.select_one("a")
                            if link_tag:
                                link = link_tag["href"]
                            activities.append(
                                Activity(
                                    name=activity_base_name,
                                    url=link,
                                    type=activity_type,
                                    content=content_html,
                                )
                            )

            if activities or (name_tag and section_name):
                sections.append(Section(name=section_name, activities=activities))

        return CourseContent(title=course_title, sections=sections), None

    def resolve_course_id_by_name(
        self, query: str
    ) -> Tuple[Optional[str], Optional[List[Course]], Optional[str]]:
        """
        Resolves a course name query to a course ID by fetching enrolled courses and filtering.
        Returns:
            Tuple[Optional[str], Optional[List[Course]], Optional[str]]:
            - resolved_id (str if single match, else None)
            - matches (list of Course objects matching query)
            - error (str if failure, else None)
        """
        courses, error = self.get_courses()
        if error:
            return None, None, error

        if not courses:
            return None, [], None

        query_lower = query.lower()
        matches = []
        for course in courses:
            if query_lower in course.title.lower() or query_lower in course.id:
                matches.append(course)

        if len(matches) == 1:
            return matches[0].id, matches, None
        return None, matches, None

    def get_categories(
        self, category_id: Optional[str] = None
    ) -> Tuple[Optional[CategoryBrowseResult], Optional[str]]:
        """Browse course categories and courses within a category."""
        if category_id:
            url = f"https://ekursy.put.poznan.pl/course/index.php?categoryid={category_id}"
        else:
            url = "https://ekursy.put.poznan.pl/course/index.php"

        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            return None, f"Failed to access course categories: {e}"

        soup = BeautifulSoup(resp.text, "html.parser")
        main_region = soup.select_one("#region-main") or soup.find("div", role="main") or soup

        # 1. Identify current category (if any)
        current_category = None
        if category_id:
            header_el = (
                main_region.select_one(".page-header-headings h1")
                or main_region.select_one("h2")
                or soup.select_one("h1")
            )
            cat_name = header_el.get_text(strip=True) if header_el else f"Category {category_id}"
            current_category = CourseCategory(
                id=category_id,
                name=cat_name,
                url=url,
            )

        # 2. Extract subcategories
        subcategories: List[CourseCategory] = []
        seen_cat_ids = set()

        cat_links = main_region.find_all("a", href=re.compile(r"categoryid=(\d+)"))
        for a_tag in cat_links:
            href = a_tag.get("href", "")
            if "lang=" in href:
                continue
            cat_match = re.search(r"categoryid=(\d+)", href)
            if not cat_match:
                continue
            cid = cat_match.group(1)
            if category_id and cid == category_id:
                continue
            if cid in seen_cat_ids:
                continue

            name = a_tag.get_text(strip=True)
            if not name or name in ["Zobacz więcej", "View"]:
                continue

            seen_cat_ids.add(cid)
            subcategories.append(
                CourseCategory(
                    id=cid,
                    name=name,
                    url=urljoin("https://ekursy.put.poznan.pl/", href),
                )
            )

        # 3. Extract courses
        courses: List[DiscoveredCourse] = []
        seen_course_ids = set()

        courseboxes = main_region.select(".coursebox")
        for box in courseboxes:
            title_tag = box.select_one(".coursename a")
            # If the box links to categoryid= instead of course/view.php, it's a category box
            if title_tag and "categoryid=" in title_tag.get("href", ""):
                continue

            cid = box.get("data-courseid")
            if not cid and title_tag and title_tag.get("href"):
                cid_match = re.search(r"id=(\d+)", title_tag["href"])
                if cid_match:
                    cid = cid_match.group(1)

            if not cid or cid in seen_course_ids:
                continue


            seen_course_ids.add(cid)
            title = title_tag.get_text(strip=True) if title_tag else "Unknown Course"
            course_url = (
                title_tag["href"]
                if title_tag and title_tag.get("href")
                else f"https://ekursy.put.poznan.pl/course/view.php?id={cid}"
            )

            requires_key = bool(
                box.select(".enrolmenticons .fa-key")
                or box.select(".enrolmenticons i[title*='klucz' i]")
                or box.select(".enrolmenticons i[title*='key' i]")
                or box.select("img[src*='key']")
            )

            summary_tag = box.select_one(".content .summary") or box.select_one(".summary")
            summary = summary_tag.get_text(strip=True) if summary_tag else None

            courses.append(
                DiscoveredCourse(
                    id=cid,
                    title=title,
                    url=course_url,
                    category_name=current_category.name if current_category else None,
                    requires_key=requires_key,
                    summary=summary,
                )
            )

        # Fallback if no .coursebox found, check direct course/view.php links in region
        if not courses:
            for a_tag in main_region.find_all("a", href=re.compile(r"course/view\.php\?id=(\d+)")):
                href = a_tag["href"]
                cid_match = re.search(r"id=(\d+)", href)
                if not cid_match:
                    continue
                cid = cid_match.group(1)
                if cid in seen_course_ids:
                    continue
                title = a_tag.get_text(strip=True)
                if not title or len(title) < 2 or title in ["Zobacz więcej", "View"]:
                    continue

                seen_course_ids.add(cid)
                courses.append(
                    DiscoveredCourse(
                        id=cid,
                        title=title,
                        url=f"https://ekursy.put.poznan.pl/course/view.php?id={cid}",
                        category_name=current_category.name if current_category else None,
                        requires_key=False,
                    )
                )

        return CategoryBrowseResult(
            current_category=current_category,
            subcategories=subcategories,
            courses=courses,
        ), None

    def search_all_courses(
        self, query: str
    ) -> Tuple[Optional[List[DiscoveredCourse]], Optional[str]]:
        """Search global eKursy course catalog via course/search.php."""
        url = f"https://ekursy.put.poznan.pl/course/search.php?search={quote_plus(query)}"
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            return None, f"Failed to search courses: {e}"

        soup = BeautifulSoup(resp.text, "html.parser")
        main_region = soup.select_one("#region-main") or soup.find("div", role="main") or soup

        courses: List[DiscoveredCourse] = []
        seen_course_ids = set()

        for box in main_region.select(".coursebox"):
            cid = box.get("data-courseid")
            title_tag = box.select_one(".coursename a")
            if not cid and title_tag and title_tag.get("href"):
                cid_match = re.search(r"id=(\d+)", title_tag["href"])
                if cid_match:
                    cid = cid_match.group(1)

            if not cid or cid in seen_course_ids:
                continue

            seen_course_ids.add(cid)
            title = title_tag.get_text(strip=True) if title_tag else "Unknown Course"
            course_url = (
                title_tag["href"]
                if title_tag and title_tag.get("href")
                else f"https://ekursy.put.poznan.pl/course/view.php?id={cid}"
            )

            requires_key = bool(
                box.select(".enrolmenticons .fa-key")
                or box.select(".enrolmenticons i[title*='klucz' i]")
                or box.select(".enrolmenticons i[title*='key' i]")
                or box.select("img[src*='key']")
            )

            cat_tag = box.select_one(".categoryname")
            category_name = cat_tag.get_text(strip=True) if cat_tag else None

            summary_tag = box.select_one(".content .summary") or box.select_one(".summary")
            summary = summary_tag.get_text(strip=True) if summary_tag else None

            courses.append(
                DiscoveredCourse(
                    id=cid,
                    title=title,
                    url=course_url,
                    category_name=category_name,
                    requires_key=requires_key,
                    summary=summary,
                )
            )

        return courses, None

    def resolve_course_id_from_all_courses(
        self, query: str
    ) -> Tuple[Optional[str], Optional[List[DiscoveredCourse]], Optional[str]]:
        """
        Resolves a course name query to a course ID by searching the global course catalog.
        Returns:
            Tuple[Optional[str], Optional[List[DiscoveredCourse]], Optional[str]]:
            - resolved_id (str if single match, else None)
            - matches (list of DiscoveredCourse objects matching query)
            - error (str if failure, else None)
        """
        courses, error = self.search_all_courses(query)
        if error:
            return None, None, error

        if not courses:
            return None, [], None

        query_lower = query.lower()
        exact_matches = [c for c in courses if query_lower == c.title.lower() or query == c.id]
        if len(exact_matches) == 1:
            return exact_matches[0].id, exact_matches, None

        if len(courses) == 1:
            return courses[0].id, courses, None

        return None, courses, None

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

