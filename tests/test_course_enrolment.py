import unittest
from unittest.mock import MagicMock

import requests

from put_esys.models.course import EnrolmentStatus
from put_esys.services.ekursy.courses import CourseService


class TestCourseEnrolment(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock(spec=requests.Session)
        self.service = CourseService(self.session)

    def test_get_categories_top_level(self):
        html = """
        <div id="region-main">
            <div class="subcategories">
                <div class="category">
                    <h3 class="categoryname">
                        <a href="https://ekursy.put.poznan.pl/course/index.php?categoryid=4">WIiT</a>
                    </h3>
                </div>
                <div class="category">
                    <h3 class="categoryname">
                        <a href="https://ekursy.put.poznan.pl/course/index.php?categoryid=2">WA</a>
                    </h3>
                </div>
            </div>
        </div>
        """
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.url = "https://ekursy.put.poznan.pl/course/index.php"
        self.session.get.return_value = mock_resp

        result, error = self.service.get_categories()
        self.assertIsNone(error)
        self.assertIsNotNone(result)
        self.assertEqual(len(result.subcategories), 2)
        self.assertEqual(result.subcategories[0].id, "4")
        self.assertEqual(result.subcategories[0].name, "WIiT")
        self.assertEqual(result.subcategories[1].id, "2")
        self.assertEqual(result.subcategories[1].name, "WA")

    def test_get_categories_with_courses(self):
        html = """
        <div id="region-main">
            <div class="page-header-headings">
                <h1>II Semestr [WIiT-SI-st-II]</h1>
            </div>
            <div class="courses category-browse">
                <div class="coursebox" data-courseid="35839">
                    <h3 class="coursename">
                        <a href="https://ekursy.put.poznan.pl/course/view.php?id=35839">
                            Information Theory Methods
                        </a>
                    </h3>

                    <div class="enrolmenticons">
                        <i class="icon fa fa-key" title="Klucz dostępu do kursu"></i>
                    </div>
                </div>
                <div class="coursebox" data-courseid="35135">
                    <h3 class="coursename">
                        <a href="https://ekursy.put.poznan.pl/course/view.php?id=35135">ML Ops</a>
                    </h3>
                </div>
            </div>
        </div>
        """
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.url = "https://ekursy.put.poznan.pl/course/index.php?categoryid=3160"
        self.session.get.return_value = mock_resp

        result, error = self.service.get_categories("3160")
        self.assertIsNone(error)
        self.assertIsNotNone(result)
        self.assertEqual(result.current_category.id, "3160")
        self.assertEqual(result.current_category.name, "II Semestr [WIiT-SI-st-II]")
        self.assertEqual(len(result.courses), 2)

        c1 = result.courses[0]
        self.assertEqual(c1.id, "35839")
        self.assertEqual(c1.title, "Information Theory Methods")
        self.assertTrue(c1.requires_key)

        c2 = result.courses[1]
        self.assertEqual(c2.id, "35135")
        self.assertEqual(c2.title, "ML Ops")
        self.assertFalse(c2.requires_key)

    def test_search_all_courses(self):
        html = """
        <div id="region-main">
            <div class="coursebox" data-courseid="35839">
                <h3 class="coursename">
                    <a href="https://ekursy.put.poznan.pl/course/view.php?id=35839">
                        Information Theory Methods
                    </a>
                </h3>

                <span class="categoryname">II Semestr [WIiT-SI-st-II]</span>
                <div class="enrolmenticons">
                    <i class="icon fa fa-key" title="Klucz dostępu"></i>
                </div>
            </div>
        </div>
        """
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.url = "https://ekursy.put.poznan.pl/course/search.php?search=information"
        self.session.get.return_value = mock_resp

        courses, error = self.service.search_all_courses("information")
        self.assertIsNone(error)
        self.assertEqual(len(courses), 1)
        self.assertEqual(courses[0].id, "35839")
        self.assertEqual(courses[0].category_name, "II Semestr [WIiT-SI-st-II]")
        self.assertTrue(courses[0].requires_key)

    def test_get_enrolment_info_requires_password(self):
        html = """
        <div id="region-main">
            <h2>Information Theory Methods</h2>
            <form action="https://ekursy.put.poznan.pl/enrol/index.php" method="post">
                <input type="hidden" name="id" value="35839" />
                <input type="hidden" name="instance" value="107375" />
                <input type="hidden" name="sesskey" value="test_sesskey" />
                <input type="password" name="enrolpassword" id="id_enrolpassword" />
                <input type="submit" name="submitbutton" value="Zapisz mnie" />
            </form>
        </div>
        """
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.url = "https://ekursy.put.poznan.pl/enrol/index.php?id=35839"
        self.session.get.return_value = mock_resp

        info, error = self.service.get_enrolment_info("35839")
        self.assertIsNone(error)
        self.assertIsNotNone(info)
        self.assertEqual(info.status, EnrolmentStatus.CAN_ENROL_KEY_REQUIRED)
        self.assertTrue(info.requires_password)
        self.assertEqual(info.instance_id, "107375")
        self.assertEqual(info.sesskey, "test_sesskey")

    def test_get_enrolment_info_self_enrolment_disabled(self):
        html = """
        <div id="region-main">
            <h2>AI in Cryptography</h2>
            <p>You cannot enrol yourself in this course.</p>
        </div>
        """
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.url = "https://ekursy.put.poznan.pl/enrol/index.php?id=48570"
        self.session.get.return_value = mock_resp

        info, error = self.service.get_enrolment_info("48570")
        self.assertIsNone(error)
        self.assertIsNotNone(info)
        self.assertEqual(info.status, EnrolmentStatus.NO_SELF_ENROLMENT)

    def test_enrol_course_success(self):
        get_html = """
        <div id="region-main">
            <h2>Information Theory Methods</h2>
            <form action="https://ekursy.put.poznan.pl/enrol/index.php" method="post">
                <input type="hidden" name="id" value="35839" />
                <input type="hidden" name="instance" value="107375" />
                <input type="hidden" name="sesskey" value="test_sesskey" />
                <input type="password" name="enrolpassword" />
            </form>
        </div>
        """
        get_resp = MagicMock()
        get_resp.text = get_html
        get_resp.url = "https://ekursy.put.poznan.pl/enrol/index.php?id=35839"
        self.session.get.return_value = get_resp

        post_resp = MagicMock()
        post_resp.url = "https://ekursy.put.poznan.pl/course/view.php?id=35839"
        post_resp.text = "<h1>Course Main Page</h1>"
        self.session.post.return_value = post_resp

        success, msg = self.service.enrol_course("35839", "correct_key")
        self.assertTrue(success)
        self.assertIn("Successfully enrolled", msg)

    def test_enrol_course_invalid_key(self):
        get_html = """
        <div id="region-main">
            <h2>Information Theory Methods</h2>
            <form action="https://ekursy.put.poznan.pl/enrol/index.php" method="post">
                <input type="hidden" name="id" value="35839" />
                <input type="hidden" name="instance" value="107375" />
                <input type="hidden" name="sesskey" value="test_sesskey" />
                <input type="password" name="enrolpassword" />
            </form>
        </div>
        """
        get_resp = MagicMock()
        get_resp.text = get_html
        get_resp.url = "https://ekursy.put.poznan.pl/enrol/index.php?id=35839"
        self.session.get.return_value = get_resp

        post_resp = MagicMock()
        post_resp.url = "https://ekursy.put.poznan.pl/enrol/index.php?id=35839"
        post_resp.text = """
        <div id="region-main">
            <span class="error">Niepoprawny klucz dostępu, spróbuj ponownie.</span>
            <input type="password" name="enrolpassword" />
        </div>
        """
        self.session.post.return_value = post_resp

        success, msg = self.service.enrol_course("35839", "wrong_key")
        self.assertFalse(success)
        self.assertIn("Enrolment failed", msg)


if __name__ == "__main__":
    unittest.main()
