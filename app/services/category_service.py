from __future__ import annotations

from sqlalchemy import func, select, update

from app.database.db import DatabaseError, session_scope
from app.models import Category, Prompt
from app.services.dto import CategoryDTO

NAME_MAX = 60


def _clean(name: str) -> str:
    name = " ".join(name.split())
    if not name:
        raise ValueError("name_required")
    return name[:NAME_MAX]


class CategoryService:
    @staticmethod
    def list() -> list[CategoryDTO]:
        with session_scope() as s:
            rows = s.execute(
                select(Category.id, Category.name, func.count(Prompt.id))
                .outerjoin(Prompt, (Prompt.category_id == Category.id) & (Prompt.is_archived.is_(False)))
                .group_by(Category.id).order_by(Category.id)
            ).all()
            return [CategoryDTO(r[0], r[1], r[2]) for r in rows]

    @staticmethod
    def _exists(s, name: str, exclude_id: int | None = None) -> bool:
        stmt = select(Category.id).where(func.lower(Category.name) == name.casefold().lower())
        if exclude_id is not None:
            stmt = stmt.where(Category.id != exclude_id)
        return s.scalar(stmt) is not None

    @staticmethod
    def create(name: str) -> CategoryDTO:
        name = _clean(name)
        with session_scope() as s:
            if CategoryService._exists(s, name):
                raise ValueError("exists")
            c = Category(name=name)
            s.add(c)
            s.flush()
            return CategoryDTO(c.id, c.name, 0)

    @staticmethod
    def rename(category_id: int, name: str) -> None:
        name = _clean(name)
        with session_scope() as s:
            c = s.get(Category, category_id)
            if c is None:
                raise LookupError("category_missing")
            if CategoryService._exists(s, name, exclude_id=category_id):
                raise ValueError("exists")
            c.name = name

    @staticmethod
    def delete(category_id: int) -> None:
        """Prompts are moved to 'Other' (created if missing); deleting 'Other' uncategorises them."""
        with session_scope() as s:
            c = s.get(Category, category_id)
            if c is None:
                return
            target: int | None = None
            if c.name.casefold() != "other":
                other = s.scalar(select(Category).where(func.lower(Category.name) == "other"))
                if other is None:
                    other = Category(name="Other")
                    s.add(other)
                    s.flush()
                target = other.id
            s.execute(update(Prompt).where(Prompt.category_id == category_id).values(category_id=target))
            s.delete(c)

    @staticmethod
    def other_id() -> int | None:
        with session_scope() as s:
            return s.scalar(select(Category.id).where(func.lower(Category.name) == "other"))


__all__ = ["CategoryService", "DatabaseError"]
