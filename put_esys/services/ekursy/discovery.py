"""
Course catalog search, category browsing, and course name disambiguation services.
"""

import re
from typing import List, Optional, Tuple
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

from put_esys.models.course import (
    CategoryBrowseResult,
    Course,
    CourseCategory,
    DiscoveredCourse,
)


class CourseDiscoveryService:
    """Handles global course search, category tree browsing, and name resolution."""

    def __init__(self, session: requests.Session):
        self.session = session

    def resolve_course_id_by_name(
        self, courses: List[Course], query: str
    ) -> Tuple[Optional[str], List[Course]]:
        """
        Resolves a course name query against an enrolled courses list.
        Returns: (resolved_id, matching_courses)
        """
        if not courses:
            return None, []

        query_lower = query.lower()
        matches = []
        for course in courses:
            if query_lower in course.title.lower() or query_lower in course.id:
                matches.append(course)

        if len(matches) == 1:
            return matches[0].id, matches
        return None, matches

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
