import re

from markdownify import markdownify


def html_to_markdown(
    html_content: str, strip_images: bool = True, format_links: bool = True
) -> str:
    """
    Converts HTML content to Markdown.
    Optionally strips images and formats links to display URLs explicitly as [Text] (URL).
    """
    if not html_content:
        return ""

    md_text = markdownify(html_content)

    if strip_images:
        md_text = re.sub(r"!\[.*?\]\(.*?\)", "", md_text)

    if format_links:
        # Replaces [Text](URL) with [Text] (URL) for better CLI readability
        link_pattern = r"\[([^\]]+)\]\((https?://[^\)]+)\)"
        md_text = re.sub(link_pattern, r"[\1] (\2)", md_text)

    return md_text.strip()


def markdown_to_html_with_math(markdown_text: str) -> str:
    """
    Converts markdown text to HTML, while preserving and converting LaTeX math formulas
    from $$...$$ to \\[...\\] and $...$ to \\(...\\) for Moodle compatibility.
    """
    if not markdown_text:
        return ""

    # 1. Extract block math $$...$$
    block_math = []

    def replace_block(match):
        block_math.append(match.group(1))
        return f"<!--BLOCK_MATH_{len(block_math) - 1}-->"

    temp_text = re.sub(r"\$\$(.*?)\$\$", replace_block, markdown_text, flags=re.DOTALL)

    # 2. Extract inline math $...$ (ignoring escaped dollar signs)
    inline_math = []

    def replace_inline(match):
        inline_math.append(match.group(1))
        return f"<!--INLINE_MATH_{len(inline_math) - 1}-->"

    inline_regex = re.compile(r"(?<!\\)\$(?!\s)([^\$\n]+?)(?<!\s)(?<!\\)\$")
    temp_text = inline_regex.sub(replace_inline, temp_text)

    # 3. Render Markdown to HTML
    from markdown_it import MarkdownIt

    md = MarkdownIt("js-default", {"html": True})
    html_text = md.render(temp_text)

    # 4. Restore block math with \[ ... \]
    for i, math in enumerate(block_math):
        html_text = html_text.replace(f"<!--BLOCK_MATH_{i}-->", f"\\[{math}\\]")

    # 5. Restore inline math with \( ... \)
    for i, math in enumerate(inline_math):
        html_text = html_text.replace(f"<!--INLINE_MATH_{i}-->", f"\\({math}\\)")

    return html_text
