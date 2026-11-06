import unittest

from put_esys.models.quiz import Question, QuizAttemptDetails
from put_esys.services.ekursy.quiz_sync import QuizSyncService


class TestQuizSyncService(unittest.TestCase):
    def test_dump_and_parse_roundtrip(self):
        questions = [
            Question(
                number="1",
                state="Answer saved",
                type="essay",
                allows_attachments=False,
                text="<p>Explain Shannon entropy.</p>",
                answer="<p>H(X) = -sum p(x) log p(x)</p>",
                attachments=[],
                comment="<p>Good explanation.</p>",
            ),
            Question(
                number="2",
                state="Not yet answered",
                type="shortanswer",
                allows_attachments=False,
                text="<p>What is 2+2?</p>",
                answer="",
                attachments=[],
            ),
        ]
        details = QuizAttemptDetails(
            quiz_id=101,
            attempt_id=202,
            questions=questions,
        )

        md_output = QuizSyncService.dump_to_markdown(details)
        self.assertIn("# Quiz Attempt 202 (Quiz ID: 101)", md_output)
        self.assertIn("=== QUESTION 1 ===", md_output)
        self.assertIn("=== QUESTION 2 ===", md_output)

        attempt_id, answers = QuizSyncService.parse_markdown_dump(md_output)
        self.assertEqual(attempt_id, "202")
        self.assertIn(1, answers)
        self.assertIn(2, answers)
        self.assertIn("H(X) = -sum p(x) log p(x)", answers[1])


if __name__ == "__main__":
    unittest.main()
