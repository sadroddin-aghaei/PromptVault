from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QComboBox, QFileDialog, QFormLayout, QGridLayout, QHBoxLayout, QScrollArea, QVBoxLayout,
                               QWidget)

from app import APP_NAME, APP_VERSION, COPYRIGHT, DEVELOPER
from app.database.db import DatabaseError, current_db_file
from app.services.io_service import ImportError_, IOService
from app.services.prompt_service import PromptService
from app.services.settings_service import FONT_SIZES, Settings
from app.ui.components.icons import logo_pixmap
from app.ui.components.widgets import (Card, PageHeader, confirm, label, make_button, show_error, show_info, toast)
from app.utils.i18n import LANGUAGES, digits, num, t
from app.utils.paths import data_dir

APPEARANCE_KEYS = ("language", "theme", "font_size")


class SettingsPage(QWidget):
    appearanceChanged = Signal()
    dataChanged = Signal()

    def __init__(self, settings: Settings, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Page")
        self.settings = settings
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(widgetResizable=True)
        outer.addWidget(scroll)
        body = QWidget(objectName="Page")
        scroll.setWidget(body)
        lay = QVBoxLayout(body)
        lay.setContentsMargins(32, 28, 32, 16)
        lay.setSpacing(16)
        lay.addWidget(PageHeader(t("set_title"), t("set_subtitle")))

        # Appearance
        self.lang = self._combo([(LANGUAGES[c], c) for c in LANGUAGES], settings.get("language"))
        self.theme = self._combo([(t(f"theme_{k}"), k) for k in ("oled", "charcoal", "light")], settings.get("theme"))
        self.font = self._combo([(digits(str(s)) + " px", s) for s in FONT_SIZES], settings.get("font_size"))
        self.startup = self._combo([(t(f"startup_{k}"), k) for k in ("dashboard", "prompts", "last")], settings.get("startup"))
        lay.addWidget(self._section(t("set_appearance"), [(t("set_language"), self.lang), (t("set_theme"), self.theme),
                                                          (t("set_font_size"), self.font)]))
        lay.addWidget(self._section(t("set_general"), [(t("set_startup"), self.startup)]))
        for combo, key in ((self.lang, "language"), (self.theme, "theme"), (self.font, "font_size")):
            combo.currentIndexChanged.connect(lambda _i, c=combo, k=key: self._appearance(k, c.currentData()))
        self.startup.currentIndexChanged.connect(lambda _i: settings.set("startup", self.startup.currentData()))

        # Data
        card = Card()
        v = QVBoxLayout(card)
        v.setContentsMargins(20, 16, 20, 18)
        v.setSpacing(12)
        v.addWidget(label(t("set_data"), "SectionTitle"))
        loc = QHBoxLayout()
        loc.addWidget(label(t("set_data_loc") + ":", "Muted"))
        path = label(str(data_dir()))
        path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        path.setLayoutDirection(Qt.LeftToRight)
        loc.addWidget(path, 1)
        open_btn = make_button(t("open_folder"), "mdi6.folder-open-outline", "ghost")
        open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir()))))
        loc.addWidget(open_btn)
        v.addLayout(loc)
        grid = QGridLayout()
        grid.setSpacing(8)
        actions = [("backup_db", "mdi6.database-export-outline", self._backup), ("restore_db", "mdi6.database-import-outline", self._restore),
                   ("import_json", "mdi6.file-import-outline", self._import), ("export_json", "mdi6.code-json", self._export_json),
                   ("export_txt_all", "mdi6.file-document-outline", lambda: self._export_text("txt")),
                   ("export_md_all", "mdi6.file-export-outline", lambda: self._export_text("md"))]
        for i, (key, ic, fn) in enumerate(actions):
            b = make_button(t(key), ic)
            b.clicked.connect(fn)
            grid.addWidget(b, i // 3, i % 3)
        v.addLayout(grid)
        lay.addWidget(card)

        # Privacy + About
        priv = Card()
        pv = QVBoxLayout(priv)
        pv.setContentsMargins(20, 16, 20, 16)
        pv.addWidget(label(t("set_privacy"), "SectionTitle"))
        pv.addWidget(label(t("privacy_text"), "Muted", wrap=True))
        lay.addWidget(priv)

        about = Card()
        av = QHBoxLayout(about)
        av.setContentsMargins(20, 18, 20, 18)
        av.setSpacing(16)
        logo = label()
        logo.setPixmap(logo_pixmap(64))
        av.addWidget(logo, 0, Qt.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(3)
        col.addWidget(label(t("about"), "Muted"))
        col.addWidget(label(APP_NAME, "SectionTitle"))
        col.addWidget(label(t("about_text"), "Muted", wrap=True))
        col.addWidget(label(f"{t('version')}: {digits(APP_VERSION)}"))
        col.addWidget(label(f"{t('developer')}: {DEVELOPER}"))
        cp = label(COPYRIGHT)
        cp.setLayoutDirection(Qt.LeftToRight)
        cp.setTextInteractionFlags(Qt.TextSelectableByMouse)
        col.addWidget(cp)
        av.addLayout(col, 1)
        lay.addWidget(about)
        foot = label(COPYRIGHT, "Muted")
        foot.setAlignment(Qt.AlignCenter)
        lay.addWidget(foot)
        lay.addStretch(1)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _combo(items, current) -> QComboBox:
        c = QComboBox()
        c.setMinimumWidth(240)
        for text, data in items:
            c.addItem(text, data)
        c.setCurrentIndex(max(c.findData(current), 0))
        return c

    @staticmethod
    def _section(title: str, rows) -> Card:
        card = Card()
        v = QVBoxLayout(card)
        v.setContentsMargins(20, 16, 20, 18)
        v.setSpacing(12)
        v.addWidget(label(title, "SectionTitle"))
        form = QFormLayout()
        form.setHorizontalSpacing(24)
        form.setVerticalSpacing(10)
        form.setLabelAlignment(Qt.AlignLeading)
        for text, w in rows:
            form.addRow(label(text), w)
        v.addLayout(form)
        return card

    def _appearance(self, key: str, value) -> None:
        if self.settings.get(key) == value:
            return
        self.settings.set(key, value)
        QTimer.singleShot(0, self.appearanceChanged.emit)   # rebuild after this signal returns

    def _stamp(self) -> str:
        return datetime.now().strftime("%Y%m%d-%H%M")

    def _io_failure(self, exc: Exception) -> None:
        if isinstance(exc, ImportError_):
            show_error(self, t(exc.code))
        elif isinstance(exc, DatabaseError):
            show_error(self, t("db_error"))
        else:
            show_error(self, t("io_error", detail=str(exc)))

    # ------------------------------------------------------------------ data actions
    def _backup(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, t("backup_db"), f"PromptVault-backup-{self._stamp()}.db", t("filter_db"))
        if path:
            try:
                IOService.backup_database(Path(path))
                toast(self, t("backup_done"))
            except Exception as exc:
                self._io_failure(exc)

    def _restore(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, t("restore_db"), "", t("filter_db"))
        if not path:
            return
        try:
            IOService.validate_backup(Path(path))
        except Exception as exc:
            return self._io_failure(exc)
        if not confirm(self, t("restore_confirm_title"), t("restore_confirm_text"), t("restore_db"), danger=True):
            return
        try:
            IOService.restore_database(Path(path))
        except Exception as exc:
            return self._io_failure(exc)
        toast(self, t("restore_done"))
        self.dataChanged.emit()

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, t("import_json"), "", t("filter_json"))
        if not path or not confirm(self, t("import_json"), t("import_confirm"), t("import_json")):
            return
        try:
            r = IOService.import_json(Path(path))
        except Exception as exc:
            return self._io_failure(exc)
        show_info(self, t("import_json"), t("import_done", imported=num(r.imported), dup=num(r.duplicates), invalid=num(r.invalid)))
        self.dataChanged.emit()

    def _export_json(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, t("export_json"), f"PromptVault-{self._stamp()}.json", t("filter_json"))
        if path:
            try:
                toast(self, t("export_done", n=num(IOService.export_json(Path(path)))))
            except Exception as exc:
                self._io_failure(exc)

    def _export_text(self, fmt: str) -> None:
        prompts = PromptService.search(archived=None, sort="oldest")
        if not prompts:
            return show_info(self, t("export"), t("nothing_to_export"))
        path, _ = QFileDialog.getSaveFileName(self, t("export"), f"PromptVault-{self._stamp()}.{fmt}",
                                              t("filter_md" if fmt == "md" else "filter_txt"))
        if path:
            try:
                toast(self, t("export_done", n=num(IOService.export_text(Path(path), prompts, fmt))))
            except Exception as exc:
                self._io_failure(exc)
