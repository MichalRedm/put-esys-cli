import unittest
from unittest.mock import MagicMock

import requests

from put_esys.services.ekursy.courses import CourseService


class TestCourseDownloadAndNotes(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock(spec=requests.Session)
        self.service = CourseService(self.session)

    def test_extract_filename_rfc5987_utf8(self):
        resp = MagicMock(spec=requests.Response)
        resp.headers = {
            "Content-Disposition": "attachment; filename*=UTF-8''%C5%9Bci%C4%85ga.pdf"
        }
        resp.url = "https://ekursy.put.poznan.pl/mod/resource/view.php?id=123"

        fn = CourseService._extract_filename_from_response(resp)
        self.assertEqual(fn, "ściąga.pdf")

    def test_extract_filename_standard_and_mojibake_healing(self):
        resp = MagicMock(spec=requests.Response)
        # Latin-1 bytes of UTF-8 encoded "ściąga.pdf"
        resp.headers = {
            "Content-Disposition": 'attachment; filename="\xc5\x9bci\xc4\x85ga.pdf"'
        }
        resp.url = "https://ekursy.put.poznan.pl/mod/resource/view.php?id=123"

        fn = CourseService._extract_filename_from_response(resp)
        self.assertEqual(fn, "ściąga.pdf")

    def test_extract_filename_fallback_url(self):
        resp = MagicMock(spec=requests.Response)
        resp.headers = {}
        resp.url = "https://ekursy.put.poznan.pl/pluginfile.php/123/mod_folder/content/0/test_dataset.csv?forcedownload=1"

        fn = CourseService._extract_filename_from_response(resp)
        self.assertEqual(fn, "test_dataset.csv")

    def test_section_summary_and_availability_parsing(self):
        html = """
        <h1>Sample Course</h1>
        <ul class="topics">
            <li class="section" id="section-1">
                <h3 class="sectionname">Lab 1</h3>
                <div class="summary">
                    <p>Welcome to <strong>Lab 1</strong>. Please complete the tasks below.</p>
                </div>
                <ul class="section">
                    <li class="activity modtype_resource isrestricted" id="module-101">
                        <div class="activityname">
                            <a href="https://ekursy.put.poznan.pl/mod/resource/view.php?id=101">Instructions.pdf</a>
                        </div>
                        <div class="availabilityinfo isrestricted">
                            Available from 1 October 2026, 9:40 AM
                        </div>
                    </li>
                    <li class="activity modtype_folder" id="module-102">
                        <div class="activityname">
                            <a href="https://ekursy.put.poznan.pl/mod/folder/view.php?id=102">Datasets</a>
                        </div>
                    </li>
                </ul>
            </li>
        </ul>
        """
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.url = "https://ekursy.put.poznan.pl/course/view.php?id=999"
        self.session.get.return_value = mock_resp

        content, error = self.service.get_course_content("999")
        self.assertIsNone(error)
        self.assertIsNotNone(content)
        self.assertEqual(len(content.sections), 1)

        sec = content.sections[0]
        self.assertEqual(sec.name, "Lab 1")
        self.assertIn("Welcome to **Lab 1**", sec.summary)

        act1 = sec.activities[0]
        self.assertEqual(act1.name, "Instructions.pdf")
        self.assertTrue(act1.is_restricted)
        self.assertIn("Available from 1 October 2026", act1.availability_info)

        act2 = sec.activities[1]
        self.assertEqual(act2.name, "Datasets")
        self.assertFalse(act2.is_restricted)

    def test_export_course_notes(self):
        html = """
        <h1>Sample Course</h1>
        <ul class="topics">
            <li class="section" id="section-1">
                <h3 class="sectionname">Theory</h3>
                <div class="summary">
                    <p>Entropy definition: H(X) = -sum p(x) log p(x)</p>
                </div>
                <ul class="section">
                    <li class="activity modtype_assign" id="module-201">
                        <div class="activityname">
                            <a href="https://ekursy.put.poznan.pl/mod/assign/view.php?id=201">
                                Assignment 1
                            </a>
                        </div>
                    </li>
                </ul>
            </li>
        </ul>
        """
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.url = "https://ekursy.put.poznan.pl/course/view.php?id=999"
        self.session.get.return_value = mock_resp

        notes, error = self.service.export_course_notes("999")
        self.assertIsNone(error)
        self.assertIsNotNone(notes)
        self.assertIn("# Sample Course", notes)
        self.assertIn("## Theory", notes)
        self.assertIn("Entropy definition", notes)
        expected_link = "[Assignment 1](https://ekursy.put.poznan.pl/mod/assign/view.php?id=201)"
        self.assertIn(expected_link, notes)


if __name__ == "__main__":
    unittest.main()
