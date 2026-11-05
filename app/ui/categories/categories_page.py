from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QInputDialog, QLineEdit, QScrollArea, QVBoxLayout, QWidget

from app.database.db import DatabaseError
from app.services.category_service import CategoryService
from app.ui.components.icons import icon
from app.ui.components.widgets import (Card, ElidedLabel, PageHeader, confirm, label, make_button, show_error, toast)
from app.utils.i18n import category_label, num, t


class CategoriesPage(QWidget):
    openCategory = Signal(int)
    dataChanged = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Page")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 16)
        outer.setSpacing(16)
        outer.addWidget(PageHeader(t("cat_title"), t("cat_subtitle")))
        add = QHBoxLayout()
        self.name = QLineEdit(placeholderText=t("cat_new_ph"))
        self.name.setMaxLength(60)
        self.name.setMinimumHeight(40)
        self.add_btn = make_button(t("add"), "mdi6.plus", "primary")
        add.addWidget(self.name, 1)
        add.addWidget(self.add_btn)
        outer.addLayout(add)
        scroll = QScrollArea(widgetResizable=True)
        body = QWidget(objectName="Page")
        self.rows = QVBoxLayout(body)
        self.rows.setContentsMargins(0, 0, 4, 0)
        self.rows.setSpacing(8)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        self.add_btn.clicked.connect(self._add)
        self.name.returnPressed.connect(self._add)

    def refresh(self) -> None:
        while self.rows.count():
            it = self.rows.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        try:
            cats = CategoryService.list()
        except DatabaseError:
            return show_error(self, t("db_error"))
        for c in cats:
            card = Card(hoverable=True)
            h = QHBoxLayout(card)
            h.setContentsMargins(16, 10, 10, 10)
            h.addWidget(ElidedLabel(category_label(c.name)), 1)
            h.addWidget(label(t("cat_prompts", n=num(c.count)), "Chip"))
            for text, ic, variant, fn in ((t("view"), "mdi6.text-box-multiple-outline", "ghost", lambda _=0, i=c.id: self.openCategory.emit(i)),
                                          (t("rename"), "mdi6.pencil-outline", "ghost", lambda _=0, x=c: self._rename(x)),
                                          (t("delete"), "mdi6.delete-outline", "ghost", lambda _=0, x=c: self._delete(x))):
                b = make_button("", ic, variant, text)
                b.clicked.connect(fn)
                h.addWidget(b)
            self.rows.addWidget(card)
        self.rows.addStretch(1)

    def _err(self, exc: Exception) -> None:
        if isinstance(exc, ValueError):
            show_error(self, t("cat_exists" if str(exc) == "exists" else "cat_name_required"))
        else:
            show_error(self, t("db_error"))

    def _add(self) -> None:
        if not self.name.text().strip():
            return
        try:
            CategoryService.create(self.name.text())
        except (ValueError, DatabaseError) as exc:
            return self._err(exc)
        self.name.clear()
        self.refresh()
        self.dataChanged.emit()

    def _rename(self, c) -> None:
        text, ok = QInputDialog.getText(self, t("cat_rename_title"), t("cat_rename_label"), QLineEdit.Normal,
                                        category_label(c.name))
        if ok:
            try:
                CategoryService.rename(c.id, text)
            except (ValueError, DatabaseError, LookupError) as exc:
                return self._err(exc)
            self.refresh()
            self.dataChanged.emit()

    def _delete(self, c) -> None:
        msg = t("cat_delete_text_other") if c.name.casefold() == "other" else t("cat_delete_text", name=category_label(c.name))
        if confirm(self, t("delete"), msg, t("delete"), danger=True):
            try:
                CategoryService.delete(c.id)
            except DatabaseError as exc:
                return self._err(exc)
            toast(self, t("cat_deleted"))
            self.refresh()
            self.dataChanged.emit()
