from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database.db import session_scope
from app.models import Category, Prompt, Tag
from app.services.dto import PromptDTO, PromptInput

TITLE_MAX, DESC_MAX, TAG_MAX = 300, 2000, 40
SORTS = ("newest", "oldest", "recent", "modified")


def normalize_tags(tags: list[str]) -> list[str]:
    out: dict[str, str] = {}
    for raw in tags:
        name = " ".join(raw.split())[:TAG_MAX]
        if name:
            out.setdefault(name.casefold(), name)
    return list(out.values())


def parse_tags(text: str) -> list[str]:
    """Split a user-typed tag string (supports Latin and Persian commas)."""
    for sep in ("،", ";", "\n"):
        text = text.replace(sep, ",")
    return normalize_tags(text.split(","))


def _dto(p: Prompt) -> PromptDTO:
    return PromptDTO(
        id=p.id, title=p.title, description=p.description or "", content=p.content or "",
        category_id=p.category_id, category_name=p.category.name if p.category else None,
        tags=sorted((t.name for t in p.tags), key=str.casefold),
        is_favorite=p.is_favorite, is_archived=p.is_archived,
        created_at=p.created_at, updated_at=p.updated_at, last_used_at=p.last_used_at, use_count=p.use_count,
    )


def _resolve_tags(s: Session, names: list[str]) -> list[Tag]:
    names = normalize_tags(names)
    if not names:
        return []
    existing = {t.name.casefold(): t for t in s.scalars(select(Tag))}
    result = []
    for n in names:
        tag = existing.get(n.casefold())
        if tag is None:
            tag = Tag(name=n)
            s.add(tag)
            existing[n.casefold()] = tag
        result.append(tag)
    return result


def _validate(data: PromptInput) -> PromptInput:
    title = " ".join(data.title.split())
    if not title:
        raise ValueError("title_required")
    data.title = title[:TITLE_MAX]
    data.description = data.description.strip()[:DESC_MAX]
    data.content = data.content.replace("\r\n", "\n").replace("\r", "\n")
    return data


def _like(term: str) -> str:
    return "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


class PromptService:
    @staticmethod
    def create(data: PromptInput) -> PromptDTO:
        data = _validate(data)
        with session_scope() as s:
            now = datetime.now()
            p = Prompt(title=data.title, description=data.description, content=data.content,
                       category_id=data.category_id, is_favorite=data.is_favorite,
                       is_archived=data.is_archived, created_at=now, updated_at=now)
            p.tags = _resolve_tags(s, data.tags)
            s.add(p)
            s.flush()
            s.refresh(p)
            return _dto(p)

    @staticmethod
    def update(prompt_id: int, data: PromptInput) -> PromptDTO:
        data = _validate(data)
        with session_scope() as s:
            p = s.get(Prompt, prompt_id)
            if p is None:
                raise LookupError("prompt_missing")
            p.title, p.description, p.content = data.title, data.description, data.content
            p.category_id, p.is_favorite, p.is_archived = data.category_id, data.is_favorite, data.is_archived
            p.tags = _resolve_tags(s, data.tags)
            p.updated_at = datetime.now()
            s.flush()
            s.refresh(p)
            return _dto(p)

    @staticmethod
    def get(prompt_id: int) -> PromptDTO | None:
        with session_scope() as s:
            p = s.get(Prompt, prompt_id)
            return _dto(p) if p else None

    @staticmethod
    def delete(prompt_id: int) -> None:
        with session_scope() as s:
            p = s.get(Prompt, prompt_id)
            if p is not None:
                s.delete(p)

    @staticmethod
    def duplicate(prompt_id: int, suffix: str = "copy") -> PromptDTO:
        with session_scope() as s:
            src = s.get(Prompt, prompt_id)
            if src is None:
                raise LookupError("prompt_missing")
            now = datetime.now()
            p = Prompt(title=f"{src.title} ({suffix})"[:TITLE_MAX], description=src.description,
                       content=src.content, category_id=src.category_id, is_favorite=False,
                       is_archived=False, created_at=now, updated_at=now)
            p.tags = list(src.tags)
            s.add(p)
            s.flush()
            s.refresh(p)
            return _dto(p)

    @staticmethod
    def set_favorite(prompt_id: int, value: bool) -> None:
        with session_scope() as s:
            if (p := s.get(Prompt, prompt_id)) is not None:
                p.is_favorite = value

    @staticmethod
    def set_archived(prompt_id: int, value: bool) -> None:
        with session_scope() as s:
            if (p := s.get(Prompt, prompt_id)) is not None:
                p.is_archived = value

    @staticmethod
    def mark_used(prompt_id: int) -> None:
        with session_scope() as s:
            if (p := s.get(Prompt, prompt_id)) is not None:
                p.last_used_at = datetime.now()
                p.use_count = (p.use_count or 0) + 1

    @staticmethod
    def search(query: str = "", category_id: int | None = None, favorites_only: bool = False,
               archived: bool | None = False, sort: str = "newest", limit: int | None = None) -> list[PromptDTO]:
        """archived: False = active only, True = archived only, None = everything."""
        stmt = select(Prompt).options(selectinload(Prompt.tags), joinedload(Prompt.category))
        if archived is not None:
            stmt = stmt.where(Prompt.is_archived == archived)
        if category_id is not None:
            stmt = stmt.where(Prompt.category_id == category_id)
        if favorites_only:
            stmt = stmt.where(Prompt.is_favorite.is_(True))
        for term in query.split():
            like = _like(term)
            stmt = stmt.where(or_(
                Prompt.title.ilike(like, escape="\\"),
                Prompt.content.ilike(like, escape="\\"),
                Prompt.description.ilike(like, escape="\\"),
                Prompt.tags.any(Tag.name.ilike(like, escape="\\")),
            ))
        if sort == "oldest":
            stmt = stmt.order_by(Prompt.created_at.asc(), Prompt.id.asc())
        elif sort == "recent":
            stmt = stmt.order_by(Prompt.last_used_at.is_(None), Prompt.last_used_at.desc(), Prompt.id.desc())
        elif sort == "modified":
            stmt = stmt.order_by(Prompt.updated_at.desc(), Prompt.id.desc())
        else:
            stmt = stmt.order_by(Prompt.created_at.desc(), Prompt.id.desc())
        if limit:
            stmt = stmt.limit(limit)
        with session_scope() as s:
            return [_dto(p) for p in s.scalars(stmt).unique()]

    @staticmethod
    def count(query: str = "", category_id: int | None = None, favorites_only: bool = False,
              archived: bool | None = False) -> int:
        return len(PromptService.search(query, category_id, favorites_only, archived))

    @staticmethod
    def stats() -> dict:
        with session_scope() as s:
            active = Prompt.is_archived.is_(False)
            total = s.scalar(select(func.count(Prompt.id)).where(active)) or 0
            favs = s.scalar(select(func.count(Prompt.id)).where(active, Prompt.is_favorite.is_(True))) or 0
            archived = s.scalar(select(func.count(Prompt.id)).where(Prompt.is_archived.is_(True))) or 0
            used = s.scalar(select(func.count(Prompt.id)).where(active, Prompt.last_used_at.is_not(None))) or 0
            cats = s.scalar(select(func.count(Category.id))) or 0
        return {"total": total, "favorites": favs, "archived": archived, "used": used, "categories": cats}

    @staticmethod
    def recently_used(limit: int = 5) -> list[PromptDTO]:
        with session_scope() as s:
            stmt = (select(Prompt).options(selectinload(Prompt.tags), joinedload(Prompt.category))
                    .where(Prompt.is_archived.is_(False), Prompt.last_used_at.is_not(None))
                    .order_by(Prompt.last_used_at.desc()).limit(limit))
            return [_dto(p) for p in s.scalars(stmt).unique()]

    @staticmethod
    def recently_added(limit: int = 5) -> list[PromptDTO]:
        return PromptService.search(sort="newest", limit=limit)
