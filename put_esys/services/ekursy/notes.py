"""
Course notes markdown generation service.
"""

from typing import Optional, Tuple

from put_esys.models.course import CourseContent
from put_esys.utils.markdown import html_to_markdown


class CourseNotesExporter:
    """Generates clean Markdown notes from course content, sections, and activities."""

    @staticmethod
    def export(course_id: str, content: CourseContent) -> Tuple[Optional[str], Optional[str]]:
        """Exports all section announcements, summaries, labels, and activity lists as Markdown."""
        if not content:
            return None, "No course content provided."

        lines = [
            f"# {content.title}",
            f"\nCourse ID: {course_id}  ",
            f"Course URL: https://ekursy.put.poznan.pl/course/view.php?id={course_id}\n",
            "---\n",
        ]

        for section in content.sections:
            lines.append(f"## {section.name}\n")
            if section.summary:
                lines.append(f"{section.summary}\n")

            if section.activities:
                lines.append("### Activities & Materials\n")
                for act in section.activities:
                    lock_str = f" 🔒 *({act.availability_info})*" if act.is_restricted else ""
                    if act.url:
                        lines.append(f"- [{act.name}]({act.url}) (`{act.type}`){lock_str}")
                    else:
                        lines.append(f"- **{act.name}** (`{act.type}`){lock_str}")

                    if act.content:
                        clean_content = html_to_markdown(act.content).strip()
                        if clean_content:
                            indented = "\n".join(
                                f"  > {line}" for line in clean_content.splitlines()
                            )
                            lines.append(f"{indented}\n")

                    if act.children:
                        for ch in act.children:
                            if ch.url:
                                lines.append(f"  - [{ch.name}]({ch.url})")
                            else:
                                lines.append(f"  - {ch.name}")
                lines.append("")

            lines.append("---\n")

        return "\n".join(lines), None
