import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture()
def vault(tmp_path, monkeypatch):
    monkeypatch.setenv("PROMPT_VAULT_HOME", str(tmp_path))
    from app.database.db import init_db, shutdown_db
    init_db()
    yield tmp_path
    shutdown_db()
