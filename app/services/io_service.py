"""Import / export / backup / restore with validation and data-loss protection."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select

from app import APP_NAME, APP_VERSION
from app.database.db import DatabaseError, current_db_file, init_db, session_scope, shutdown_db
from app.models import Category, Prompt, Tag
from app.services.dto import PromptDTO
from app.services.prompt_service import DESC_MAX, TITLE_MAX, PromptService, normalize_tags
from app.utils.paths import backups_dir

MAX_IMPORT_BYTES = 25 * 1024 * 1024
MAX_CONTENT = 500_000
FORMAT_VERSION = 1
KEEP_AUTO_BACKUPS = 10


class ImportError_(Exception):
    """User-facing import/restore validation failure. `.code` is an i18n key."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(code)
        self.code, self.detail = code, detail


@dataclass
class ImportResult:
    imported: int = 0
    duplicates: int = 0
    invalid: int = 0
    categories_created: int = 0
    safety_backup: Path | None = None
    errors: list[str] = field(default_factory=list)


def _atomic_write(path: Path, text: str) -> None:
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".pv_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------- export
def _prompt_to_json(p: PromptDTO) -> dict:
    return {
        "title": p.title, "description": p.description, "content": p.content,
        "category": p.category_name, "tags": p.tags,
        "is_favorite": p.is_favorite, "is_archived": p.is_archived,
        "created_at": p.created_at.isoformat(timespec="seconds"),
        "updated_at": p.updated_at.isoformat(timespec="seconds"),
    }


class IOService:
    @staticmethod
    def export_json(path: Path, prompts: list[PromptDTO] | None = None) -> int:
        prompts = prompts if prompts is not None else PromptService.search(archived=None, sort="oldest")
        with session_scope() as s:
            cats = list(s.scalars(select(Category.name).order_by(Category.id)))
        doc = {"app": APP_NAME, "app_version": APP_VERSION, "format_version": FORMAT_VERSION,
               "exported_at": datetime.now().isoformat(timespec="seconds"),
               "categories": cats, "prompts": [_prompt_to_json(p) for p in prompts]}
        _atomic_write(path, json.dumps(doc, ensure_ascii=False, indent=2))
        return len(prompts)

    @staticmethod
    def export_text(path: Path, prompts: list[PromptDTO], fmt: str = "md") -> int:
        chunks = [_to_markdown(p) if fmt == "md" else _to_txt(p) for p in prompts]
        sep = "\n\n---\n\n" if fmt == "md" else "\n\n" + "=" * 60 + "\n\n"
        _atomic_write(path, sep.join(chunks) + "\n")
        return len(prompts)

    # ---------------------------------------------------------------- import
    @staticmethod
    def import_json(path: Path) -> ImportResult:
        path = Path(path)
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise ImportError_("import_unreadable", str(exc)) from exc
        if size > MAX_IMPORT_BYTES:
            raise ImportError_("import_too_large")
        try:
            doc = json.loads(path.read_text(encoding="utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ImportError_("import_not_json", str(exc)) from exc
        items = doc.get("prompts") if isinstance(doc, dict) else doc
        if not isinstance(items, list):
            raise ImportError_("import_bad_schema")

        result = ImportResult()
        valid = []
        for i, raw in enumerate(items):
            item = _validate_item(raw)
            if item is None:
                result.invalid += 1
                if len(result.errors) < 20:
                    result.errors.append(f"#{i + 1}")
            else:
                valid.append(item)
        if not valid and result.invalid:
            raise ImportError_("import_no_valid")

        result.safety_backup = IOService.auto_backup("pre-import")  # protect against data loss
        try:
            with session_scope() as s:  # single transaction: all or nothing
                cats = {c.name.casefold(): c for c in s.scalars(select(Category))}
                seen = {(t, c) for t, c in s.execute(select(Prompt.title, Prompt.content))}
                tags = {t.name.casefold(): t for t in s.scalars(select(Tag))}
                for it in valid:
                    key = (it["title"], it["content"])
                    if key in seen:
                        result.duplicates += 1
                        continue
                    seen.add(key)
                    cat = None
                    if it["category"]:
                        cat = cats.get(it["category"].casefold())
                        if cat is None:
                            cat = Category(name=it["category"][:60])
                            s.add(cat)
                            s.flush()
                            cats[cat.name.casefold()] = cat
                            result.categories_created += 1
                    p = Prompt(title=it["title"], description=it["description"], content=it["content"],
                               category_id=cat.id if cat else None, is_favorite=it["is_favorite"],
                               is_archived=it["is_archived"], created_at=it["created_at"], updated_at=it["updated_at"])
                    for name in it["tags"]:
                        tag = tags.get(name.casefold())
                        if tag is None:
                            tag = Tag(name=name)
                            s.add(tag)
                            tags[name.casefold()] = tag
                        p.tags.append(tag)
                    s.add(p)
                    result.imported += 1
        except DatabaseError:
            raise
        return result

    # ---------------------------------------------------------------- backup / restore
    @staticmethod
    def backup_database(dest: Path) -> Path:
        dest = Path(dest)
        src = sqlite3.connect(str(current_db_file()))
        try:
            dst = sqlite3.connect(str(dest))
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
        return dest

    @staticmethod
    def auto_backup(tag: str) -> Path | None:
        try:
            dest = backups_dir() / f"promptvault-{tag}-{datetime.now():%Y%m%d-%H%M%S}.db"
            IOService.backup_database(dest)
            old = sorted(backups_dir().glob("promptvault-*.db"), key=lambda p: p.stat().st_mtime)
            for p in old[:-KEEP_AUTO_BACKUPS]:
                p.unlink(missing_ok=True)
            return dest
        except (OSError, sqlite3.Error):
            return None

    @staticmethod
    def validate_backup(path: Path) -> None:
        path = Path(path)
        if not path.is_file():
            raise ImportError_("restore_unreadable")
        try:
            con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
            try:
                if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ImportError_("restore_corrupt")
                names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not {"prompts", "categories", "tags"} <= names:
                    raise ImportError_("restore_not_vault")
            finally:
                con.close()
        except sqlite3.DatabaseError as exc:
            raise ImportError_("restore_not_vault", str(exc)) from exc

    @staticmethod
    def restore_database(src: Path) -> Path | None:
        IOService.validate_backup(src)
        safety = IOService.auto_backup("pre-restore")
        target = current_db_file()
        tmp = target.with_suffix(".restore.tmp")
        shutil.copyfile(src, tmp)
        shutdown_db()
        try:
            for ext in ("-wal", "-shm", "-journal"):
                Path(str(target) + ext).unlink(missing_ok=True)
            os.replace(tmp, target)
        finally:
            tmp.unlink(missing_ok=True)
            init_db(target)
        return safety


def _validate_item(raw) -> dict | None:
    if not isinstance(raw, dict):
        return None
    title, content = raw.get("title"), raw.get("content", "")
    if not isinstance(title, str) or not isinstance(content, str):
        return None
    title = " ".join(title.split())[:TITLE_MAX]
    if not title or len(content) > MAX_CONTENT:
        return None
    desc = raw.get("description") or ""
    cat = raw.get("category")
    tags = raw.get("tags") or []
    if not isinstance(desc, str) or not isinstance(tags, list) or (cat is not None and not isinstance(cat, str)):
        return None
    now = datetime.now()
    return {
        "title": title, "content": content.replace("\r\n", "\n"), "description": desc.strip()[:DESC_MAX],
        "category": " ".join(cat.split()) if cat and cat.strip() else None,
        "tags": normalize_tags([t for t in tags if isinstance(t, str)]),
        "is_favorite": bool(raw.get("is_favorite", False)), "is_archived": bool(raw.get("is_archived", False)),
        "created_at": _dt(raw.get("created_at"), now), "updated_at": _dt(raw.get("updated_at"), now),
    }


def _dt(value, default: datetime) -> datetime:
    try:
        return datetime.fromisoformat(value) if isinstance(value, str) else default
    except ValueError:
        return default


def _fence(text: str) -> str:
    longest = run = 0
    for ch in text:
        run = run + 1 if ch == "`" else 0
        longest = max(longest, run)
    return "`" * max(3, longest + 1)


def _to_markdown(p: PromptDTO) -> str:
    lines = [f"# {p.title}", ""]
    if p.description:
        lines += [f"> {p.description}", ""]
    meta = []
    if p.category_name:
        meta.append(f"**Category:** {p.category_name}")
    if p.tags:
        meta.append("**Tags:** " + ", ".join(f"`{t}`" for t in p.tags))
    if meta:
        lines += ["  \n".join(meta), ""]
    f = _fence(p.content)
    lines += [f + "text", p.content, f]
    return "\n".join(lines)


def _to_txt(p: PromptDTO) -> str:
    lines = [p.title, "-" * min(60, max(3, len(p.title)))]
    if p.description:
        lines.append(p.description)
    if p.category_name:
        lines.append(f"Category: {p.category_name}")
    if p.tags:
        lines.append("Tags: " + ", ".join(p.tags))
    return "\n".join(lines + ["", p.content])
