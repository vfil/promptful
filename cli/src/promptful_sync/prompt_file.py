"""Read/write the git-tracked, on-disk form of a Prompt's Live Version.

See CONTEXT.md's "Local Sync" section (Prompt File) and
docs/adr/0009-local-sync-via-git-tracked-prompt-files.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

# The frontmatter block is delimited by a "---" line immediately followed by a
# newline, both at the top of the file and closing it. Splitting on this exact
# separator (not bare "---") means a maxsplit=2 split leaves `text` byte-for-byte
# untouched, even if `text` itself later contains a "---" line.
_FRONTMATTER_DELIMITER = "---\n"


@dataclass
class ParsedPromptFile:
    role: str
    text: str


def write_prompt_file(path: Path, *, role: str, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{_FRONTMATTER_DELIMITER}role: {role}\n{_FRONTMATTER_DELIMITER}{text}")


def parse_prompt_file(path: Path) -> ParsedPromptFile:
    raw = path.read_text()
    _, frontmatter, text = raw.split(_FRONTMATTER_DELIMITER, 2)
    meta = yaml.safe_load(frontmatter)
    return ParsedPromptFile(role=meta["role"], text=text)


def slug_to_path(slug: str, *, root: Path) -> Path:
    return root / f"{slug.lstrip('/')}.prompt.md"


def path_to_slug(path: Path, *, root: Path) -> str:
    relative = path.relative_to(root).as_posix().removesuffix(".prompt.md")
    return f"/{relative}"
