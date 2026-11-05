"""Filesystem locations. Nothing is hardcoded: user data lives in the OS user-data dir."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def resource_path(*parts: str) -> Path:
    """Path to a bundled read-only resource (works in dev and inside PyInstaller)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base.joinpath(*parts)


def data_dir() -> Path:
    """Persistent per-user data directory (never the temporary install/extract dir)."""
    override = os.environ.get("PROMPT_VAULT_HOME")
    if override:
        path = Path(override)
    elif sys.platform.startswith("win"):
        path = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / "PromptVault"
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / "PromptVault"
    else:
        path = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "PromptVault"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sub(name: str) -> Path:
    p = data_dir() / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def db_path() -> Path:
    return data_dir() / "promptvault.db"


def settings_path() -> Path:
    return data_dir() / "settings.json"


def backups_dir() -> Path:
    return _sub("backups")


def cache_dir() -> Path:
    return _sub("cache")


def log_path() -> Path:
    return data_dir() / "promptvault.log"
