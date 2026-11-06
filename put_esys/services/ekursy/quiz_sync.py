"""
Quiz attempt Markdown serialization and synchronization services.
"""

import re
from typing import Dict, Optional, Tuple

from put_esys.models.quiz import QuizAttemptDetails
from put_esys.utils.markdown import html_to_markdown


class QuizSyncService:
    """Handles serializing quiz attempts to Markdown and parsing local edits to sync back."""

    @staticmethod
    def dump_to_markdown(details: QuizAttemptDetails) -> str:
        """Serializes quiz attempt details into structured Markdown template format."""
        lines = [f"# Quiz Attempt {details.attempt_id} (Quiz ID: {details.quiz_id})\n"]

        for q in details.questions:
            lines.append(f"=== QUESTION {q.number} ===")
            lines.append(f"Type: {q.type}")
            lines.append(f"State: {q.state}\n")

            q_text = html_to_markdown(q.text)
            lines.append("## Question Text")
            lines.append(q_text)
            lines.append("")

            a_text = html_to_markdown(q.answer)
            lines.append("## Current Answer")
            lines.append(a_text)
            lines.append("")

            if q.comment:
                c_text = html_to_markdown(q.comment)
                lines.append("## Teacher Comment")
                lines.append(c_text)
                lines.append("")

            lines.append("")  # extra spacing

        return "\n".join(lines)

    @staticmethod
    def parse_markdown_dump(content: str) -> Tuple[Optional[str], Dict[int, str]]:
        """
        Parses Markdown template content.
        Returns:
            Tuple of (attempt_id, local_answers_dict mapping question_number -> answer_text)
        """
        attempt_id_match = re.search(r"Quiz Attempt (\d+)", content)
        attempt_id = attempt_id_match.group(1) if attempt_id_match else None

        parts = content.split("=== QUESTION ")
        local_answers: Dict[int, str] = {}
        for part in parts[1:]:
            lines = part.split("\n")
            if not lines:
                continue
            number_line = lines[0]
            q_no = number_line.replace("===", "").strip()
            if not q_no.isdigit():
                continue

            subparts = part.split("## Current Answer")
            if len(subparts) > 1:
                ans_content = subparts[1].strip()
                comment_split = ans_content.split("## Teacher Comment")
                ans_text = comment_split[0].strip()
                local_answers[int(q_no)] = ans_text

        return attempt_id, local_answers
