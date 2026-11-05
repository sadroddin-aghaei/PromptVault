"""Engine / session management. All access goes through `session_scope`."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL, Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.models import DEFAULT_CATEGORIES, Base, Category, Meta
from app.utils.paths import db_path

log = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Raised for any database failure; the transaction has been rolled back."""


_engine: Engine | None = None
_factory: sessionmaker[Session] | None = None


def init_db(path: Path | None = None) -> Engine:
    global _engine, _factory
    shutdown_db()
    path = Path(path) if path else db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(URL.create("sqlite", database=str(path)), future=True)

    @event.listens_for(engine, "connect")
    def _pragmas(conn, _record):  # pragma: no cover - trivial
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    try:
        Base.metadata.create_all(engine)
    except SQLAlchemyError as exc:
        engine.dispose()
        raise DatabaseError(str(exc)) from exc
    _engine, _factory = engine, sessionmaker(engine, expire_on_commit=False, future=True)
    _seed()
    return engine


def shutdown_db() -> None:
    global _engine, _factory
    if _engine is not None:
        _engine.dispose()
    _engine = _factory = None


def current_db_file() -> Path:
    if _engine is None or not _engine.url.database:
        raise DatabaseError("Database is not initialised")
    return Path(_engine.url.database)


@contextmanager
def session_scope() -> Iterator[Session]:
    if _factory is None:
        raise DatabaseError("Database is not initialised")
    session = _factory()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        log.exception("Database error")
        raise DatabaseError(str(exc)) from exc
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _seed() -> None:
    """Create the default categories exactly once (users may later delete them)."""
    with session_scope() as s:
        if s.get(Meta, "seeded") is None:
            if s.query(Category).count() == 0:
                s.add_all(Category(name=n) for n in DEFAULT_CATEGORIES)
            s.add(Meta(key="seeded", value="1"))
