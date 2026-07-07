from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Prompt:
    """A prompt's current Live Version: id, slug, and raw (unrendered) text.

    Named `Prompt` for call-site ergonomics even though it's technically a
    Live Version snapshot in CONTEXT.md's stricter terms (Prompt=entity,
    Version=snapshot) — a deliberate, considered divergence, not a modeling
    mistake. See sdk/README.md.
    """

    id: str
    slug: str
    leaf_slug: str
    category_id: str
    version: int
    role: str
    text: str
    is_deleted: bool
    created_at: datetime


@dataclass(frozen=True)
class PromptSummary:
    """One entry from Client.list_prompts() — no `text`, for lightweight listing."""

    id: str
    slug: str
    leaf_slug: str
    category_id: str
    version: int
    created_at: datetime
