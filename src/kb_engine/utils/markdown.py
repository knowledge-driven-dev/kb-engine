"""Markdown parsing utilities."""

from typing import Any

import frontmatter


def extract_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Extract YAML frontmatter from markdown content.

    Returns a tuple of (metadata dict, content without frontmatter).
    """
    try:
        post = frontmatter.loads(content)
        return dict(post.metadata), post.content
    except Exception:
        return {}, content


def parse_markdown_sections(
    content: str,
) -> list[tuple[list[str], str]]:
    """Parse markdown content into sections with heading paths.

    Returns a list of (heading_path, section_content) tuples.
    """
    sections: list[tuple[list[str], str]] = []
    current_path: list[str] = []
    current_content: list[str] = []
    current_levels: list[int] = []

    lines = content.split("\n")

    for line in lines:
        if line.startswith("#"):
            # Save previous section
            section_text = "\n".join(current_content).strip()
            if section_text:
                sections.append((list(current_path), section_text))
            current_content = []

            # Parse heading
            level = len(line) - len(line.lstrip("#"))
            heading_text = line.lstrip("#").strip()

            # Update path
            while current_levels and current_levels[-1] >= level:
                current_levels.pop()
                if current_path:
                    current_path.pop()

            current_path.append(heading_text)
            current_levels.append(level)
        else:
            current_content.append(line)

    # Don't forget last section
    section_text = "\n".join(current_content).strip()
    if section_text:
        sections.append((list(current_path), section_text))

    return sections
