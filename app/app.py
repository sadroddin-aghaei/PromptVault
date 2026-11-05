"""Application controller: appearance, fonts, window (re)building."""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from app.database.db import init_db
from app.services.settings_service import Settings
from app.styles.theme import build_qss, palette
from app.ui.components.icons import app_icon, set_icon_colors
from app.ui.main_window import MainWindow
from app.utils import i18n
from app.utils.paths import resource_path

log = logging.getLogger(__name__)
FONT_FILES = ("Regular", "Medium", "SemiBold", "Bold")


def load_fonts() -> bool:
    ok = False
    for w in FONT_FILES:
        path = resource_path("assets", "fonts", f"Vazirmatn-{w}.ttf")
        if path.exists() and QFontDatabase.addApplicationFont(str(path)) >= 0:
            ok = True
    if not ok:
        log.warning("Vazirmatn font not found; falling back to system fonts")
    return ok


class AppController:
    def __init__(self, qapp: QApplication):
        self.qapp = qapp
        self.settings = Settings()
        qapp.setWindowIcon(app_icon())
        load_fonts()
        init_db()
        self.window: MainWindow | None = None
        self._apply_appearance()
        start = {"dashboard": "dashboard", "prompts": "prompts", "last": self.settings.get("last_page")}[self.settings.get("startup")]
        self._show(start)

    def _apply_appearance(self) -> None:
        s = self.settings
        i18n.set_language(s.get("language"))
        rtl = i18n.is_rtl()
        self.qapp.setLayoutDirection(Qt.RightToLeft if rtl else Qt.LeftToRight)
        pal = palette(s.get("theme"))
        set_icon_colors(pal["text"], pal["muted"])
        font = QFont("Vazirmatn")
        font.setPixelSize(s.get("font_size"))
        self.qapp.setFont(font)
        self.qapp.setStyleSheet(build_qss(s.get("theme"), s.get("font_size"), rtl))

    def _show(self, page: str) -> None:
        self.window = MainWindow(self.settings, self, page)
        self.window.show()

    def rebuild(self) -> None:
        """Re-create the window after language/theme/font/restore changes."""
        old = self.window
        page = old.current if old else "dashboard"
        if old is not None:
            if not old.prompts.confirm_leave():
                return
            old.settings.set("geometry", bytes(old.saveGeometry().toBase64()).decode())
        self._apply_appearance()
        self._show(page)
        if old is not None:
            old.force_close()
            old.deleteLater()
