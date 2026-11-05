import re
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.services.prompt_service import PromptService
from app.utils import i18n


@pytest.fixture()
def ctrl(vault):
    from app.app import AppController
    app = QApplication.instance() or QApplication([])
    c = AppController(app)
    yield c
    if c.window:
        c.window.force_close()


def test_every_translation_key_exists():
    src = "".join(p.read_text(encoding="utf-8") for p in Path("app").rglob("*.py") if p.name != "i18n.py")
    used = set(re.findall(r'\bt\("([a-z_0-9]+)"', src))
    used |= {f"{p}_{k}" for p, ks in (("sort", ("newest", "oldest", "recent", "modified")), ("theme", ("oled", "charcoal", "light")),
                                      ("startup", ("dashboard", "prompts", "last")), ("nav", ("dashboard", "prompts", "categories", "settings")))
             for k in ks}
    used |= {"import_unreadable", "import_too_large", "import_not_json", "import_bad_schema", "import_no_valid",
             "restore_unreadable", "restore_corrupt", "restore_not_vault"}
    for lang in ("en", "fa"):
        missing = [k for k in used if k not in i18n.STRINGS[lang]]
        assert not missing, (lang, missing)
    assert set(i18n.STRINGS["en"]) == set(i18n.STRINGS["fa"])


def test_default_language_is_persian_rtl(ctrl):
    assert i18n.lang() == "fa" and QApplication.layoutDirection() == Qt.RightToLeft


def test_create_edit_search_copy_flow(ctrl):
    w = ctrl.window
    w.new_prompt()
    ed = w.prompts.editor
    ed.title.setText("پرامپت آزمایشی")
    ed.content.setPlainText("Explain {{topic}} to a {{role}} در {{language}}")
    ed.tags.setText("تست، demo")
    assert ed.is_dirty() and ed._var_names == ["topic", "role", "language"]
    ed._var_edits["topic"].setText("کوانتوم")
    assert ed.save() and not ed.is_dirty()
    pid = ed.prompt_id()
    stored = PromptService.get(pid)
    assert stored.content.startswith("Explain {{topic}}") and stored.tags == ["demo", "تست"]   # raw template stored
    ed.copy()
    assert QApplication.clipboard().text() == "Explain کوانتوم to a {{role}} در {{language}}"
    assert PromptService.get(pid).use_count == 1
    w.prompts.search.setText("کوانتوم")      # not in stored content -> no result
    w.prompts.refresh()
    assert w.prompts.list.count() == 0
    w.prompts.search.setText("demo")
    w.prompts.refresh()
    assert w.prompts.list.count() == 1
    ed.title.setText("changed")
    assert ed.is_dirty() and "●" in ed.state.text()


def test_unsaved_guard_blocks_navigation(ctrl, monkeypatch):
    w = ctrl.window
    w.new_prompt()
    w.prompts.editor.title.setText("x")
    monkeypatch.setattr("app.ui.prompts.prompts_page.ask_unsaved", lambda *_: "cancel")
    assert w.navigate("settings") is False and w.current == "prompts"
    monkeypatch.setattr("app.ui.prompts.prompts_page.ask_unsaved", lambda *_: "discard")
    assert w.navigate("settings") is True and w.current == "settings"


def test_language_switch_rebuilds_ui(ctrl):
    ctrl.settings.set("language", "en")
    ctrl.rebuild()
    assert i18n.lang() == "en" and QApplication.layoutDirection() == Qt.LeftToRight
    assert ctrl.window.nav_buttons["prompts"].text() == "Prompts"
    ctrl.settings.set("language", "fa")
    ctrl.settings.set("theme", "light")
    ctrl.rebuild()
    assert ctrl.window.nav_buttons["prompts"].text() == "پرامپت‌ها" and QApplication.layoutDirection() == Qt.RightToLeft


def test_categories_page_and_dashboard(ctrl):
    w = ctrl.window
    w.navigate("categories")
    w.categories.name.setText("دسته من")
    w.categories._add()
    from app.services.category_service import CategoryService
    assert "دسته من" in [c.name for c in CategoryService.list()]
    w.navigate("dashboard")
    assert w.dashboard.stats["categories"].text() in ("۱۱", "11")
