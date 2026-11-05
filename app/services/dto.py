from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PromptInput:
    title: str
    content: str = ""
    description: str = ""
    category_id: int | None = None
    tags: list[str] = field(default_factory=list)
    is_favorite: bool = False
    is_archived: bool = False


@dataclass
class PromptDTO:
    id: int
    title: str
    description: str
    content: str
    category_id: int | None
    category_name: str | None
    tags: list[str]
    is_favorite: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None
    use_count: int


@dataclass
class CategoryDTO:
    id: int
    name: str
    count: int = 0
