from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLineEdit, QProgressBar, QScrollArea, QVBoxLayout, QWidget)

from app.database.db import DatabaseError
from app.services.category_service import CategoryService
from app.services.dto import PromptDTO
from app.services.prompt_service import PromptService
from app.ui.components.icons import icon
from app.ui.components.widgets import (Card, ClickableFrame, ElidedLabel, PageHeader, add_shadow, label, make_button,
                                       show_error)
from app.utils.i18n import category_label, format_dt, num, t


def _clear(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            _clear(item.layout())


class StatCard(Card):
    def __init__(self, icon_name: str, caption: str, accent: str, shadow: bool):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(6)
        top = QHBoxLayout()
        ic = label()
        ic.setPixmap(icon(icon_name, accent).pixmap(22, 22))
        top.addWidget(ic)
        top.addStretch(1)
        lay.addLayout(top)
        self.value = label("0", "StatValue")
        lay.addWidget(self.value)
        lay.addWidget(label(caption, "Muted"))
        if shadow:
            add_shadow(self)


class DashboardPage(QWidget):
    openPrompt = Signal(int)
    openPrompts = Signal(str, object)   # query, category_id
    newPrompt = Signal()

    def __init__(self, accent: str, shadows: bool, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Page")
        self._accent = accent
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(widgetResizable=True)
        outer.addWidget(scroll)
        body = QWidget(objectName="Page")
        scroll.setWidget(body)
        lay = QVBoxLayout(body)
        lay.setContentsMargins(32, 28, 32, 20)
        lay.setSpacing(20)

        head = QHBoxLayout()
        head.addWidget(PageHeader(t("dash_title"), t("dash_subtitle")), 1)
        self.new_btn = make_button(t("new_prompt"), "mdi6.plus", "primary")
        head.addWidget(self.new_btn, 0, Qt.AlignTop)
        lay.addLayout(head)

        self.search = QLineEdit(placeholderText=t("dash_search_ph"), clearButtonEnabled=True)
        self.search.addAction(icon("mdi6.magnify", "#8d8d96"), QLineEdit.LeadingPosition)
        self.search.setMinimumHeight(42)
        lay.addWidget(self.search)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.stats = {}
        for i, (key, ic, cap) in enumerate((("total", "mdi6.text-box-multiple-outline", "stat_total"),
                                            ("favorites", "mdi6.star-outline", "stat_favorites"),
                                            ("categories", "mdi6.shape-outline", "stat_categories"),
                                            ("used", "mdi6.content-copy", "stat_used"))):
            card = StatCard(ic, t(cap), accent, shadows)
            self.stats[key] = card.value
            grid.addWidget(card, 0, i)
            grid.setColumnStretch(i, 1)
        lay.addLayout(grid)

        cols = QHBoxLayout()
        cols.setSpacing(14)
        self.used_box = self._section(t("recently_used"))
        self.added_box = self._section(t("recently_added"))
        cols.addWidget(self.used_box[0], 1)
        cols.addWidget(self.added_box[0], 1)
        lay.addLayout(cols)
        self.cat_box = self._section(t("categories_overview"))
        lay.addWidget(self.cat_box[0])
        lay.addStretch(1)

        self.search.returnPressed.connect(lambda: self.openPrompts.emit(self.search.text(), None))
        self.new_btn.clicked.connect(self.newPrompt)

    def _section(self, title: str):
        card = Card()
        v = QVBoxLayout(card)
        v.setContentsMargins(18, 16, 18, 14)
        v.setSpacing(4)
        v.addWidget(label(title, "SectionTitle"))
        inner = QVBoxLayout()
        inner.setSpacing(2)
        v.addLayout(inner)
        return card, inner

    def _prompt_row(self, p: PromptDTO, when) -> ClickableFrame:
        row = ClickableFrame()
        row.setProperty("row", True)
        h = QVBoxLayout(row)
        h.setContentsMargins(10, 7, 10, 7)
        h.setSpacing(0)
        h.addWidget(ElidedLabel(p.title))
        sub = ElidedLabel(f"{category_label(p.category_name)}  ·  {format_dt(when)}")
        sub.setObjectName("Muted")
        h.addWidget(sub)
        row.clicked.connect(lambda pid=p.id: self.openPrompt.emit(pid))
        return row

    def refresh(self) -> None:
        try:
            st = PromptService.stats()
            used = PromptService.recently_used(5)
            added = PromptService.recently_added(5)
            cats = CategoryService.list()
        except DatabaseError:
            return show_error(self, t("db_error"))
        for k, lb in self.stats.items():
            lb.setText(num(st[k]))
        for box, items, key, empty in ((self.used_box, used, "last_used_at", "empty_used"),
                                       (self.added_box, added, "created_at", "empty_added")):
            _clear(box[1])
            if not items:
                lb = label(t(empty), "Muted", wrap=True)
                lb.setContentsMargins(10, 8, 10, 8)
                box[1].addWidget(lb)
            for p in items:
                box[1].addWidget(self._prompt_row(p, getattr(p, key)))
        _clear(self.cat_box[1])
        top = max([c.count for c in cats] + [1])
        for c in cats:
            row = ClickableFrame()
            row.setProperty("row", True)
            v = QVBoxLayout(row)
            v.setContentsMargins(10, 7, 10, 7)
            v.setSpacing(5)
            h = QHBoxLayout()
            h.addWidget(ElidedLabel(category_label(c.name)), 1)
            h.addWidget(label(num(c.count), "Muted"))
            v.addLayout(h)
            bar = QProgressBar(maximum=top, value=c.count, textVisible=False)
            v.addWidget(bar)
            row.clicked.connect(lambda cid=c.id: self.openPrompts.emit("", cid))
            self.cat_box[1].addWidget(row)
