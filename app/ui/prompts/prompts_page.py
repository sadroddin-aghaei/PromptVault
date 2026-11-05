"""Prompts page: filterable list on one side, editor on the other."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QMenu,
                               QSplitter, QStackedWidget, QToolButton, QVBoxLayout, QWidget)

from app.database.db import DatabaseError
from app.services.category_service import CategoryService
from app.services.dto import PromptDTO
from app.services.prompt_service import PromptService
from app.ui.components.icons import icon
from app.ui.components.widgets import (Card, ElidedLabel, add_shadow, ask_unsaved, confirm, label, make_button, repolish,
                                       show_error, toast)
from app.ui.prompts.editor import PromptEditor
from app.utils.i18n import category_label, format_dt, num, t

LIST_CAP = 200
SORT_KEYS = ("newest", "oldest", "recent", "modified")


class PromptCard(Card):
    favoriteToggled = Signal(int, bool)

    def __init__(self, p: PromptDTO, accent: str):
        super().__init__(hoverable=True)
        self.prompt_id = p.id
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 10, 10)
        lay.setSpacing(3)
        row = QHBoxLayout()
        title = ElidedLabel(p.title)
        f = title.font()
        f.setBold(True)
        title.setFont(f)
        self.star = QToolButton(cursor=Qt.PointingHandCursor, checkable=True, checked=p.is_favorite)
        self.star.setIcon(icon("mdi6.star" if p.is_favorite else "mdi6.star-outline", accent if p.is_favorite else None))
        self.star.setAutoRaise(True)
        self.star.clicked.connect(lambda on: self.favoriteToggled.emit(self.prompt_id, on))
        row.addWidget(title, 1)
        if p.is_archived:
            row.addWidget(label("🗄", "Muted"))
        row.addWidget(self.star)
        lay.addLayout(row)
        sub = ElidedLabel((p.description or p.content).replace("\n", " ").strip())
        sub.setObjectName("Muted")
        lay.addWidget(sub)
        meta = QHBoxLayout()
        meta.setSpacing(6)
        meta.addWidget(label(category_label(p.category_name), "ChipAccent"))
        for tag in p.tags[:3]:
            meta.addWidget(label(tag, "Chip"))
        meta.addStretch(1)
        meta.addWidget(label(format_dt(p.updated_at), "Muted"))
        lay.addLayout(meta)

    def set_selected(self, sel: bool) -> None:
        self.setProperty("selected", sel)
        repolish(self)


class PromptsPage(QWidget):
    dataChanged = Signal()

    def __init__(self, theme: str, accent: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Page")
        self._theme, self._accent = theme, accent
        self._current_id: int | None = None
        self._suppress = False
        self._build()
        self._timer = QTimer(self, singleShot=True, interval=140)
        self._timer.timeout.connect(self.refresh)

    # ------------------------------------------------------------------ UI
    def _build(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(24, 22, 24, 12)
        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(18)
        outer.addWidget(split)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(10)
        lv.addWidget(label(t("nav_prompts"), "PageTitle"))
        r1 = QHBoxLayout()
        self.search = QLineEdit(placeholderText=t("search_ph"), clearButtonEnabled=True)
        self.search.addAction(icon("mdi6.magnify", "#8d8d96"), QLineEdit.LeadingPosition)
        self.new_btn = make_button("", "mdi6.plus", "primary", t("new_prompt") + "  (Ctrl+N)")
        r1.addWidget(self.search, 1)
        r1.addWidget(self.new_btn)
        lv.addLayout(r1)
        r2 = QHBoxLayout()
        self.cat = QComboBox()
        self.sort = QComboBox()
        for k in SORT_KEYS:
            self.sort.addItem(t(f"sort_{k}"), k)
        r2.addWidget(self.cat, 1)
        r2.addWidget(self.sort, 1)
        lv.addLayout(r2)
        r3 = QHBoxLayout()
        self.fav = make_button(t("favorites_only"), "mdi6.star-outline", checkable=True)
        self.arch = make_button(t("show_archived"), "mdi6.archive-outline", checkable=True)
        self.count = label("", "Muted")
        r3.addWidget(self.fav)
        r3.addWidget(self.arch)
        r3.addStretch(1)
        r3.addWidget(self.count)
        lv.addLayout(r3)
        self.list = QListWidget(spacing=5, verticalScrollMode=QListWidget.ScrollPerPixel)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        lv.addWidget(self.list, 1)
        self.empty_list = label("", "Muted", wrap=True)
        self.empty_list.setAlignment(Qt.AlignCenter)
        self.empty_list.hide()
        lv.addWidget(self.empty_list)
        left.setMinimumWidth(330)
        left.setMaximumWidth(520)

        self.stack = QStackedWidget()
        empty = QWidget()
        ev = QVBoxLayout(empty)
        ev.addStretch(1)
        for text, name in ((t("empty_editor_title"), "SectionTitle"), (t("empty_editor_hint"), "Muted")):
            lb = label(text, name)
            lb.setAlignment(Qt.AlignCenter)
            ev.addWidget(lb)
        ev.addStretch(1)
        self.editor = PromptEditor(self._theme)
        self.stack.addWidget(empty)
        self.stack.addWidget(self.editor)
        split.addWidget(left)
        split.addWidget(self.stack)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([400, 760])

        self.search.textChanged.connect(lambda *_: self._timer.start())
        self.cat.currentIndexChanged.connect(lambda *_: self.refresh())
        self.sort.currentIndexChanged.connect(lambda *_: self.refresh())
        self.fav.toggled.connect(lambda *_: self.refresh())
        self.arch.toggled.connect(lambda *_: self.refresh())
        self.new_btn.clicked.connect(self.new_prompt)
        self.list.currentItemChanged.connect(self._on_item_changed)
        self.list.customContextMenuRequested.connect(self._context_menu)
        self.editor.saved.connect(self._after_save)
        self.editor.deleted.connect(self._after_remove)
        self.editor.duplicated.connect(lambda pid: self._reload_and_select(pid))
        self.editor.archivedChanged.connect(self._after_archive)
        self.editor.favoriteChanged.connect(lambda *_: self.refresh(keep=True))
        self._fill_categories()

    def _fill_categories(self, select: int | None = None) -> None:
        self.cat.blockSignals(True)
        self.cat.clear()
        self.cat.addItem(t("all_categories"), None)
        for c in CategoryService.list():
            self.cat.addItem(f"{category_label(c.name)}  ({num(c.count)})", c.id)
        self.cat.setCurrentIndex(max(self.cat.findData(select), 0))
        self.cat.blockSignals(False)

    # ------------------------------------------------------------------ public API
    def focus_search(self) -> None:
        self.search.setFocus()
        self.search.selectAll()

    def has_unsaved(self) -> bool:
        return self.editor.is_dirty()

    def confirm_leave(self) -> bool:
        """True when it is OK to leave (saved / discarded)."""
        if not self.editor.is_dirty():
            return True
        choice = ask_unsaved(self)
        if choice == "save":
            return self.editor.save()
        return choice == "discard"

    def apply_filters(self, query: str | None = None, category_id: int | None = None) -> None:
        if not self.confirm_leave():
            return
        self.search.blockSignals(True)
        self.search.setText(query or "")
        self.search.blockSignals(False)
        self._fill_categories(category_id)
        self.fav.blockSignals(True); self.fav.setChecked(False); self.fav.blockSignals(False)
        self.refresh()

    def open_prompt(self, prompt_id: int) -> None:
        if not self.confirm_leave():
            return
        p = PromptService.get(prompt_id)
        if p is None:
            return
        if p.is_archived and not self.arch.isChecked():
            self.arch.blockSignals(True); self.arch.setChecked(True); self.arch.blockSignals(False)
        self._load(p)
        self.refresh(keep=True)

    def new_prompt(self) -> None:
        if not self.confirm_leave():
            return
        self._suppress = True
        self.list.clearSelection()
        self.list.setCurrentItem(None)
        self._suppress = False
        self._current_id = None
        self.editor.load(None, default_category=self.cat.currentData() or CategoryService.other_id())
        self.stack.setCurrentWidget(self.editor)
        self._mark_selected()

    def refresh(self, keep: bool = False) -> None:
        """Re-run the query. keep=True keeps the editor untouched; otherwise a vanished selection clears it."""
        try:
            self._fill_categories_counts()
            results = PromptService.search(
                query=self.search.text(), category_id=self.cat.currentData(),
                favorites_only=self.fav.isChecked(), archived=True if self.arch.isChecked() else False,
                sort=self.sort.currentData(), limit=LIST_CAP + 1)
        except DatabaseError:
            return show_error(self, t("db_error"))
        capped = len(results) > LIST_CAP
        results = results[:LIST_CAP]
        self._suppress = True
        self.list.setUpdatesEnabled(False)
        self.list.clear()
        for p in results:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, p.id)
            card = PromptCard(p, self._accent)
            card.favoriteToggled.connect(self._toggle_fav)
            item.setSizeHint(QSize(100, 92))
            self.list.addItem(item)
            self.list.setItemWidget(item, card)
        self.list.setUpdatesEnabled(True)
        self._suppress = False
        self._mark_selected()
        self.count.setText(t("results_count", n=num(len(results))) if not capped else t("list_capped", n=num(LIST_CAP)))
        self.empty_list.setVisible(not results)
        self.list.setVisible(bool(results))
        if not results:
            self.empty_list.setText(f"{t('no_results')}\n{t('no_results_hint')}")

    def _fill_categories_counts(self) -> None:
        sel = self.cat.currentData()
        cats = CategoryService.list()
        want = [t("all_categories")] + [f"{category_label(c.name)}  ({num(c.count)})" for c in cats]
        have = [self.cat.itemText(i) for i in range(self.cat.count())]
        if want != have:
            self._fill_categories(sel)

    # ------------------------------------------------------------------ selection
    def _row_of(self, prompt_id: int | None) -> int:
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole) == prompt_id:
                return i
        return -1

    def _mark_selected(self) -> None:
        for i in range(self.list.count()):
            it = self.list.item(i)
            card = self.list.itemWidget(it)
            sel = it.data(Qt.UserRole) == self._current_id
            if isinstance(card, PromptCard):
                card.set_selected(sel)
            if sel:
                self._suppress = True
                self.list.setCurrentItem(it)
                self._suppress = False

    def _load(self, p: PromptDTO) -> None:
        self._current_id = p.id
        self.editor.load(p)
        self.stack.setCurrentWidget(self.editor)

    def _on_item_changed(self, cur: QListWidgetItem | None, _prev) -> None:
        if self._suppress or cur is None:
            return
        pid = cur.data(Qt.UserRole)
        if pid == self._current_id:
            return
        if not self.confirm_leave():
            self._mark_selected()
            return
        p = PromptService.get(pid)
        if p:
            self._load(p)
        self._mark_selected()

    # ------------------------------------------------------------------ reactions
    def _after_save(self, pid: int) -> None:
        self._current_id = pid
        self.refresh(keep=True)
        self.dataChanged.emit()

    def _after_remove(self, _pid: int) -> None:
        self._current_id = None
        self.stack.setCurrentIndex(0)
        self.refresh()
        self.dataChanged.emit()

    def _after_archive(self, pid: int) -> None:
        p = PromptService.get(pid)
        if p and p.is_archived != self.arch.isChecked():
            self._current_id = None
            self.stack.setCurrentIndex(0)
        self.refresh()
        self.dataChanged.emit()

    def _reload_and_select(self, pid: int) -> None:
        p = PromptService.get(pid)
        if p:
            self._current_id = pid
            self.editor.load(p)
            self.stack.setCurrentWidget(self.editor)
        self.refresh(keep=True)
        self.dataChanged.emit()

    def _toggle_fav(self, pid: int, on: bool) -> None:
        try:
            PromptService.set_favorite(pid, on)
        except DatabaseError:
            return show_error(self, t("db_error"))
        if pid == self._current_id and self.editor.prompt_id() == pid:
            self.editor.fav_btn.blockSignals(True)
            self.editor.fav_btn.setChecked(on)
            self.editor.fav_btn.blockSignals(False)
            self.editor._update_fav_icon()
        QTimer.singleShot(0, lambda: self.refresh(keep=True))
        self.dataChanged.emit()

    def _context_menu(self, pos) -> None:
        item = self.list.itemAt(pos)
        if item is None:
            return
        pid = item.data(Qt.UserRole)
        p = PromptService.get(pid)
        if p is None:
            return
        m = QMenu(self)
        m.addAction(icon("mdi6.content-copy"), t("copy"), lambda: (QApplication.clipboard().setText(p.content),
                                                                    PromptService.mark_used(pid), toast(self, t("copied"))))
        m.addAction(icon("mdi6.content-duplicate"), t("duplicate"), lambda: self._ctx_duplicate(pid))
        m.addAction(icon("mdi6.star-outline"), t("favorite"), lambda: self._toggle_fav(pid, not p.is_favorite))
        m.addAction(icon("mdi6.archive-arrow-up-outline" if p.is_archived else "mdi6.archive-outline"),
                    t("unarchive" if p.is_archived else "archive"), lambda: self._ctx_archive(pid, not p.is_archived))
        m.addSeparator()
        m.addAction(icon("mdi6.delete-outline"), t("delete"), lambda: self._ctx_delete(p))
        m.exec(self.list.viewport().mapToGlobal(pos))

    def _ctx_duplicate(self, pid: int) -> None:
        if not self.confirm_leave():
            return
        dup = PromptService.duplicate(pid, t("copy_suffix"))
        toast(self, t("duplicated_ok"))
        self._reload_and_select(dup.id)

    def _ctx_archive(self, pid: int, value: bool) -> None:
        PromptService.set_archived(pid, value)
        if pid == self._current_id:
            if not self.confirm_leave():
                return
            self._current_id = None
            self.stack.setCurrentIndex(0)
        self.refresh()
        self.dataChanged.emit()

    def _ctx_delete(self, p: PromptDTO) -> None:
        if not confirm(self, t("delete"), t("delete_prompt_text", title=p.title), t("delete"), danger=True):
            return
        PromptService.delete(p.id)
        if p.id == self._current_id:
            self._current_id = None
            self.editor.load(None)
            self.stack.setCurrentIndex(0)
        toast(self, t("deleted_ok"))
        self.refresh()
        self.dataChanged.emit()
