import re
from typing import List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from put_esys.models.course import Activity, Course, CourseContent, Section


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
            resp = self.session.get(url)
            resp.raise_for_status()
        except Exception as e:
            return None, f"Failed to access course page: {e}"

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
