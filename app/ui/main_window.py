from __future__ import annotations

from PySide6.QtCore import QByteArray, QEasingCurve, QPropertyAnimation, QSize, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QButtonGroup, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QMainWindow, QStackedWidget,
                               QVBoxLayout, QWidget)

from app import APP_NAME, APP_VERSION, COPYRIGHT
from app.services.settings_service import Settings
from app.styles.theme import palette
from app.ui.categories.categories_page import CategoriesPage
from app.ui.components.icons import app_icon, icon, logo_pixmap
from app.ui.components.widgets import Toast, label, make_button
from app.ui.dashboard.dashboard import DashboardPage
from app.ui.prompts.prompts_page import PromptsPage
from app.ui.settings.settings_page import SettingsPage
from app.utils.i18n import digits, t

PAGES = ("dashboard", "prompts", "categories", "settings")
NAV_ICONS = {"dashboard": "mdi6.view-dashboard-outline", "prompts": "mdi6.text-box-multiple-outline",
             "categories": "mdi6.shape-outline", "settings": "mdi6.cog-outline"}


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings, controller, start_page: str = "dashboard"):
        super().__init__()
        self.settings, self.controller = settings, controller
        self._force_close = False
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.setMinimumSize(QSize(1020, 660))
        self.resize(1280, 800)
        theme = settings.get("theme")
        pal = palette(theme)

        root = QWidget(objectName="Root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        body = QHBoxLayout()
        body.setSpacing(0)

        # sidebar
        side = QFrame(objectName="Sidebar")
        side.setFixedWidth(232)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(14, 20, 14, 14)
        sv.setSpacing(4)
        brand = QHBoxLayout()
        brand.setContentsMargins(6, 0, 0, 10)
        logo = label()
        logo.setPixmap(logo_pixmap(34))
        name_col = QVBoxLayout()
        name_col.setSpacing(0)
        name_col.addWidget(label(APP_NAME, "Logo"))
        name_col.addWidget(label(t("app_tagline"), "Tagline", wrap=True))
        brand.addWidget(logo)
        brand.addLayout(name_col, 1)
        sv.addLayout(brand)
        self.nav_group = QButtonGroup(self)
        self.nav_buttons = {}
        for i, key in enumerate(PAGES):
            b = make_button(t(f"nav_{key}"), NAV_ICONS[key], tooltip=f"Ctrl+{i + 1}")
            b.setProperty("nav", True)
            b.setProperty("variant", "")
            b.setCheckable(True)
            b.clicked.connect(lambda _c=False, k=key: self.navigate(k))
            self.nav_group.addButton(b)
            self.nav_buttons[key] = b
            sv.addWidget(b)
        sv.addStretch(1)
        ver = label(f"v{APP_VERSION}", "Muted")
        ver.setLayoutDirection(Qt.LeftToRight)
        sv.addWidget(ver, 0, Qt.AlignHCenter)

        # pages
        self.stack = QStackedWidget()
        accent = pal["accent"]
        self.dashboard = DashboardPage(accent, shadows=(theme != "oled"))
        self.prompts = PromptsPage(theme, accent)
        self.categories = CategoriesPage()
        self.settings_page = SettingsPage(settings)
        self.pages = {"dashboard": self.dashboard, "prompts": self.prompts,
                      "categories": self.categories, "settings": self.settings_page}
        for p in self.pages.values():
            self.stack.addWidget(p)
        body.addWidget(side)
        body.addWidget(self.stack, 1)
        outer.addLayout(body, 1)
        footer = label(COPYRIGHT, "Footer")
        footer.setAlignment(Qt.AlignCenter)
        footer.setLayoutDirection(Qt.LeftToRight)
        outer.addWidget(footer)
        self._toast = Toast(root)

        # wiring
        self.dashboard.openPrompt.connect(self.open_prompt)
        self.dashboard.openPrompts.connect(lambda q, cid: self.open_prompts(q, cid))
        self.dashboard.newPrompt.connect(self.new_prompt)
        self.categories.openCategory.connect(lambda cid: self.open_prompts("", cid))
        self.categories.dataChanged.connect(self._data_changed)
        self.prompts.dataChanged.connect(self._data_changed)
        self.settings_page.dataChanged.connect(self._after_restore)
        self.settings_page.appearanceChanged.connect(controller.rebuild)
        for i, key in enumerate(PAGES):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self, activated=lambda k=key: self.navigate(k))
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self.new_prompt)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: (self.navigate("prompts"), self.prompts.focus_search()))

        self.current = ""
        self.navigate(start_page, animate=False)
        geo = settings.get("geometry")
        if geo:
            self.restoreGeometry(QByteArray.fromBase64(geo.encode()))

    # ------------------------------------------------------------------ navigation
    def navigate(self, key: str, animate: bool = True) -> bool:
        if key not in self.pages:
            key = "dashboard"
        if key == self.current:
            self.nav_buttons[key].setChecked(True)
            return True
        if self.current == "prompts" and not self.prompts.confirm_leave():
            self.nav_buttons[self.current].setChecked(True)
            return False
        page = self.pages[key]
        if key in ("dashboard", "categories"):
            page.refresh()
        elif key == "prompts":
            page.refresh()
        self.stack.setCurrentWidget(page)
        self.nav_buttons[key].setChecked(True)
        self.current = key
        self.settings.set("last_page", key) if key in ("dashboard", "prompts") else None
        if animate:
            self._fade(page)
        return True

    def _fade(self, page: QWidget) -> None:
        fx = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(fx)
        anim = QPropertyAnimation(fx, b"opacity", page)
        anim.setDuration(180)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.finished.connect(lambda: page.setGraphicsEffect(None))
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def open_prompts(self, query: str = "", category_id: int | None = None) -> None:
        if self.navigate("prompts"):
            self.prompts.apply_filters(query, category_id)

    def open_prompt(self, prompt_id: int) -> None:
        if self.navigate("prompts"):
            self.prompts.open_prompt(prompt_id)

    def new_prompt(self) -> None:
        if self.navigate("prompts"):
            self.prompts.new_prompt()

    def _data_changed(self) -> None:
        pass  # dashboard/categories refresh themselves when shown

    def _after_restore(self) -> None:
        self.controller.rebuild()

    def toast(self, text: str) -> None:
        self._toast.popup(text)

    # ------------------------------------------------------------------ lifecycle
    def force_close(self) -> None:
        self._force_close = True
        self.close()

    def closeEvent(self, e) -> None:
        if not self._force_close and not self.prompts.confirm_leave():
            e.ignore()
            return
        self.settings.set("geometry", bytes(self.saveGeometry().toBase64()).decode())
        e.accept()
