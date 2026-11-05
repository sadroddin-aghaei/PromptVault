from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Table, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

DEFAULT_CATEGORIES = [
    "Programming", "Software Development", "AI & Machine Learning", "Image Generation",
    "Writing", "Marketing", "Productivity", "Education", "Business", "Other",
]


class Base(DeclarativeBase):
    pass


prompt_tags = Table(
    "prompt_tags", Base.metadata,
    Column("prompt_id", ForeignKey("prompts.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)


class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)


class Prompt(Base):
    __tablename__ = "prompts"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, default=0)

    category: Mapped[Category | None] = relationship()
    tags: Mapped[list[Tag]] = relationship(secondary=prompt_tags)

    __table_args__ = (
        Index("ix_prompts_created", "created_at"),
        Index("ix_prompts_updated", "updated_at"),
        Index("ix_prompts_used", "last_used_at"),
        Index("ix_prompts_cat", "category_id"),
        Index("ix_prompts_flags", "is_archived", "is_favorite"),
    )


class Meta(Base):
    __tablename__ = "meta"
    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(String(200), default="")
