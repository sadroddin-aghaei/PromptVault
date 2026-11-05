"""Prompt editor: fields, counters, variables panel, live preview, copy/save/etc."""
from __future__ import annotations

import html

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLineEdit, QMenu,
                               QPlainTextEdit, QPushButton, QScrollArea, QSplitter, QTextBrowser, QToolButton,
                               QVBoxLayout, QWidget)

from app.database.db import DatabaseError
from app.services.category_service import CategoryService
from app.services.dto import PromptDTO, PromptInput
from app.services.io_service import IOService
from app.services.prompt_service import PromptService, parse_tags
from app.styles.theme import MONO_STACK, palette
from app.ui.components.icons import icon
from app.ui.components.widgets import label, make_button, repolish, show_error, toast, confirm
from app.utils.i18n import category_label, digits, format_dt, is_rtl, num, t
from app.utils.variables import STANDARD_VARIABLES, VAR_RE, find_variables, fill_variables, line_direction


class PromptEditor(QWidget):
    saved = Signal(int)
    deleted = Signal(int)
    duplicated = Signal(int)
    archivedChanged = Signal(int)
    favoriteChanged = Signal(int, bool)
    dirtyChanged = Signal(bool)

    def __init__(self, theme: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._pal = palette(theme)
        self._prompt: PromptDTO | None = None
        self._dirty = False
        self._loading = False
        self._values: dict[str, str] = {}
        self._var_names: list[str] = []
        self._var_edits: dict[str, QLineEdit] = {}
        self._build()
        self._preview_timer = QTimer(self, singleShot=True, interval=90)
        self._preview_timer.timeout.connect(self._render_preview)
        QShortcut(QKeySequence.Save, self, activated=self.save, context=Qt.WidgetWithChildrenShortcut)

    # ------------------------------------------------------------------ UI
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        top = QHBoxLayout()
        self.title = QLineEdit(objectName="TitleEdit", placeholderText=t("ed_title_ph"))
        self.title.setMaxLength(300)
        self.fav_btn = QToolButton(checkable=True, cursor=Qt.PointingHandCursor, toolTip=t("favorite"))
        self.arch_btn = QToolButton(cursor=Qt.PointingHandCursor)
        self.state = label("", "SavedBadge")
        top.addWidget(self.title, 1)
        top.addWidget(self.state)
        top.addWidget(self.fav_btn)
        top.addWidget(self.arch_btn)
        root.addLayout(top)

        self.desc = QLineEdit(placeholderText=t("ed_desc_ph"))
        root.addWidget(self.desc)

        meta = QHBoxLayout()
        self.category = QComboBox()
        self.category.setMinimumWidth(190)
        self.tags = QLineEdit(placeholderText=t("ed_tags_ph"))
        self.tags.addAction(icon("mdi6.tag-outline", self._pal["muted"]), QLineEdit.LeadingPosition)
        meta.addWidget(self.category)
        meta.addWidget(self.tags, 1)
        root.addLayout(meta)

        self.content = QPlainTextEdit(placeholderText=t("ed_content_ph"))
        self.content.setTabStopDistance(32)
        self._set_direction(is_rtl())

        self.preview = QTextBrowser()
        self.preview.setOpenLinks(False)

        self.split = QSplitter(Qt.Vertical)
        self.split.setChildrenCollapsible(False)
        self.split.addWidget(self.content)
        self.split.addWidget(self.preview)
        self.split.setSizes([360, 170])
        root.addWidget(self.split, 1)

        self.var_panel = QFrame(objectName="VarPanel")
        vp = QVBoxLayout(self.var_panel)
        vp.setContentsMargins(14, 10, 14, 12)
        vp.setSpacing(6)
        head = QHBoxLayout()
        head.addWidget(label(t("variables"), "SectionTitle"))
        head.addWidget(label(t("variables_hint"), "Muted"), 1)
        vp.addLayout(head)
        self.var_grid_host = QWidget()
        self.var_grid = QGridLayout(self.var_grid_host)
        self.var_grid.setContentsMargins(0, 0, 0, 0)
        self.var_grid.setHorizontalSpacing(10)
        self.var_scroll = QScrollArea(widgetResizable=True, frameShape=QFrame.NoFrame)
        self.var_scroll.setWidget(self.var_grid_host)
        self.var_scroll.setFrameShape(QFrame.NoFrame)
        vp.addWidget(self.var_scroll)
        self.var_panel.hide()
        root.addWidget(self.var_panel)

        tools = QHBoxLayout()
        bar = QHBoxLayout()
        self.counter = label("", "Muted")
        self.mono = make_button(t("monospace"), "mdi6.code-braces", "ghost", checkable=True)
        self.prev_btn = make_button(t("preview"), "mdi6.eye-outline", "ghost", checkable=True)
        self.prev_btn.setChecked(True)
        self.dir_btn = make_button("", "mdi6.format-pilcrow-arrow-left" if is_rtl() else "mdi6.format-pilcrow-arrow-right",
                                   "ghost", t("text_direction"))
        self.var_btn = QToolButton(text=t("insert_variable"), cursor=Qt.PointingHandCursor, popupMode=QToolButton.InstantPopup)
        self.var_btn.setIcon(icon("mdi6.variable"))
        self.var_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        menu = QMenu(self.var_btn)
        for name in STANDARD_VARIABLES:
            menu.addAction("{{" + name + "}}", lambda n=name: self.content.insertPlainText("{{" + n + "}}"))
        self.var_btn.setMenu(menu)
        self.dup_btn = make_button("", "mdi6.content-duplicate", "ghost", t("duplicate"))
        self.exp_btn = QToolButton(cursor=Qt.PointingHandCursor, toolTip=t("export"), popupMode=QToolButton.InstantPopup)
        self.exp_btn.setIcon(icon("mdi6.file-export-outline"))
        em = QMenu(self.exp_btn)
        em.addAction(t("export_md"), lambda: self._export("md"))
        em.addAction(t("export_txt"), lambda: self._export("txt"))
        self.exp_btn.setMenu(em)
        self.del_btn = make_button("", "mdi6.delete-outline", "ghost", t("delete"))
        self.copy_btn = make_button(t("copy"), "mdi6.content-copy", tooltip="Ctrl+Shift+C")
        self.save_btn = make_button(t("save"), "mdi6.content-save-outline", "primary", "Ctrl+S")
        tools.addWidget(self.counter)
        tools.addStretch(1)
        for w in (self.dir_btn, self.mono, self.prev_btn, self.var_btn):
            tools.addWidget(w)
        bar.addStretch(1)
        for w in (self.dup_btn, self.exp_btn, self.del_btn, self.copy_btn, self.save_btn):
            bar.addWidget(w)
        root.addLayout(tools)
        root.addLayout(bar)

        # wiring
        for w in (self.title, self.desc, self.tags):
            w.textChanged.connect(self._mark_dirty)
        self.category.currentIndexChanged.connect(self._mark_dirty)
        self.content.textChanged.connect(self._on_content)
        self.fav_btn.toggled.connect(self._on_fav)
        self.arch_btn.clicked.connect(self._on_archive)
        self.mono.toggled.connect(self._apply_mono)
        self.dir_btn.clicked.connect(self._toggle_direction)
        self.prev_btn.toggled.connect(self.preview.setVisible)
        self.copy_btn.clicked.connect(self.copy)
        self.save_btn.clicked.connect(self.save)
        self.dup_btn.clicked.connect(self._duplicate)
        self.del_btn.clicked.connect(self._delete)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, activated=self.copy, context=Qt.WidgetWithChildrenShortcut)
        self._update_fav_icon()

    # ------------------------------------------------------------------ state
    def prompt_id(self) -> int | None:
        return self._prompt.id if self._prompt else None

    def is_dirty(self) -> bool:
        return self._dirty

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty
        self.state.setObjectName("UnsavedBadge" if dirty else "SavedBadge")
        repolish(self.state)
        if dirty:
            self.state.setText("● " + t("unsaved"))
        else:
            self.state.setText("" if self._prompt is None else t("saved_state"))
        self.save_btn.setEnabled(dirty or self._prompt is None)
        self.dirtyChanged.emit(dirty)

    def _mark_dirty(self, *_a) -> None:
        if not self._loading and not self._dirty:
            self._set_dirty(True)

    def _populate_categories(self, selected: int | None) -> None:
        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItem(t("uncategorized"), None)
        for c in CategoryService.list():
            self.category.addItem(category_label(c.name), c.id)
        idx = self.category.findData(selected)
        self.category.setCurrentIndex(max(idx, 0))
        self.category.blockSignals(False)

    def load(self, prompt: PromptDTO | None, default_category: int | None = None) -> None:
        self._loading = True
        self._prompt = prompt
        self._values.clear()
        self._populate_categories(prompt.category_id if prompt else default_category)
        self.title.setText(prompt.title if prompt else "")
        self.desc.setText(prompt.description if prompt else "")
        self.tags.setText(", ".join(prompt.tags) if prompt else "")
        self.content.setPlainText(prompt.content if prompt else "")
        first = next((ln for ln in (prompt.content if prompt else "").splitlines() if ln.strip()), "")
        self._set_direction(line_direction(first) == "rtl" if first else is_rtl())
        self.fav_btn.setChecked(bool(prompt and prompt.is_favorite))
        self._update_fav_icon()
        self._update_arch_icon()
        for w in (self.dup_btn, self.exp_btn, self.del_btn, self.arch_btn):
            w.setEnabled(prompt is not None)
        self.copy_btn.setEnabled(True)
        self._loading = False
        self._set_dirty(False)
        self._update_counter()
        self._sync_variables()
        self._render_preview()
        if prompt is None:
            self.title.setFocus()
        tip = ""
        if prompt:
            tip = f"{t('created')}: {format_dt(prompt.created_at)}\n{t('modified')}: {format_dt(prompt.updated_at)}"
            if prompt.use_count:
                tip += "\n" + t("used_times", n=num(prompt.use_count))
        self.title.setToolTip(tip)

    def set_theme(self, theme: str) -> None:
        self._pal = palette(theme)

    # ------------------------------------------------------------------ content / preview / variables
    def _on_content(self) -> None:
        self._mark_dirty()
        self._update_counter()
        self._sync_variables()
        self._preview_timer.start()

    def _update_counter(self) -> None:
        text = self.content.toPlainText()
        self.counter.setText(t("counter", c=num(len(text)), w=num(len(text.split()))))

    def _set_direction(self, rtl: bool) -> None:
        """Explicit direction + alignment (Qt does not flip AlignLeft for RTL documents)."""
        self._rtl = rtl
        self.content.setLayoutDirection(Qt.RightToLeft if rtl else Qt.LeftToRight)
        opt = self.content.document().defaultTextOption()
        opt.setTextDirection(Qt.RightToLeft if rtl else Qt.LeftToRight)
        opt.setAlignment(Qt.AlignRight if rtl else Qt.AlignLeft)
        self.content.document().setDefaultTextOption(opt)
        if hasattr(self, "dir_btn"):
            self.dir_btn.setIcon(icon("mdi6.format-pilcrow-arrow-left" if rtl else "mdi6.format-pilcrow-arrow-right"))

    def _toggle_direction(self) -> None:
        self._set_direction(not self._rtl)

    def _apply_mono(self, on: bool) -> None:
        f = self.content.font()
        if on:
            f.setFamilies(["Cascadia Mono", "Consolas", "Menlo", "DejaVu Sans Mono", "Vazirmatn"])
            f.setStyleHint(QFont.Monospace)
        else:
            f = QApplication.font()
        self.content.setFont(f)

    def _sync_variables(self) -> None:
        names = find_variables(self.content.toPlainText())
        if names == self._var_names:
            return
        self._var_names = names
        self._var_edits.clear()
        while self.var_grid.count():
            item = self.var_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        cols = 2
        for i, name in enumerate(names):
            r, c = divmod(i, cols)
            box = QHBoxLayout()
            lb = label(name, "Muted")
            lb.setMinimumWidth(80)
            ed = QLineEdit(self._values.get(name, ""), placeholderText=name)
            ed.textChanged.connect(lambda v, n=name: self._on_var(n, v))
            self._var_edits[name] = ed
            wrap = QWidget()
            box.setContentsMargins(0, 2, 0, 2)
            wrap.setLayout(box)
            box.addWidget(lb)
            box.addWidget(ed, 1)
            self.var_grid.addWidget(wrap, r, c)
        self.var_scroll.setFixedHeight(min((len(names) + 1) // 2, 3) * 44 + 4)
        self.var_panel.setVisible(bool(names))

    def _on_var(self, name: str, value: str) -> None:
        self._values[name] = value
        self._preview_timer.start()

    def _render_preview(self) -> None:
        if not self.preview.isVisible() and not self.prev_btn.isChecked():
            return
        p = self._pal
        text = self.content.toPlainText()
        out = []
        for line in text.split("\n"):
            if not line.strip():
                out.append("<div>&nbsp;</div>")
                continue
            parts, pos = [], 0
            for m in VAR_RE.finditer(line):
                parts.append(html.escape(line[pos:m.start()]))
                val = self._values.get(m.group(1), "")
                if val:
                    parts.append(f'<span style="color:{p["accent"]};font-weight:600">{html.escape(val)}</span>')
                else:
                    parts.append(f'<span style="color:{p["accent"]};background-color:{p["elevated"]}">'
                                 f'{html.escape(m.group(0))}</span>')
                pos = m.end()
            parts.append(html.escape(line[pos:]))
            d = line_direction(line)
            out.append(f'<div dir="{d}" align="{"right" if d == "rtl" else "left"}">{"".join(parts)}</div>')
        self.preview.setHtml(f'<div style="line-height:1.5">{"".join(out)}</div>')

    def result_text(self) -> str:
        return fill_variables(self.content.toPlainText(), self._values)

    # ------------------------------------------------------------------ actions
    def collect(self) -> PromptInput:
        return PromptInput(
            title=self.title.text(), description=self.desc.text(), content=self.content.toPlainText(),
            category_id=self.category.currentData(), tags=parse_tags(self.tags.text()),
            is_favorite=self.fav_btn.isChecked(), is_archived=bool(self._prompt and self._prompt.is_archived))

    def save(self) -> bool:
        if not self._dirty and self._prompt is not None:
            return True
        try:
            data = self.collect()
            self._prompt = PromptService.update(self._prompt.id, data) if self._prompt else PromptService.create(data)
        except ValueError:
            show_error(self, t("title_required"))
            self.title.setFocus()
            return False
        except (DatabaseError, LookupError):
            show_error(self, t("db_error"))
            return False
        self._loading = True
        self.title.setText(self._prompt.title)
        self._loading = False
        for w in (self.dup_btn, self.exp_btn, self.del_btn, self.arch_btn):
            w.setEnabled(True)
        self._update_arch_icon()
        self._set_dirty(False)
        toast(self, t("saved_ok"))
        self.saved.emit(self._prompt.id)
        return True

    def copy(self) -> None:
        QApplication.clipboard().setText(self.result_text())
        if self._prompt:
            try:
                PromptService.mark_used(self._prompt.id)
            except DatabaseError:
                pass
        toast(self, t("copied"))

    def _duplicate(self) -> None:
        if not self._prompt or (self._dirty and not self.save()):
            return
        try:
            dup = PromptService.duplicate(self._prompt.id, t("copy_suffix"))
        except (DatabaseError, LookupError):
            return show_error(self, t("db_error"))
        toast(self, t("duplicated_ok"))
        self.duplicated.emit(dup.id)

    def _delete(self) -> None:
        if not self._prompt:
            return
        if not confirm(self, t("delete"), t("delete_prompt_text", title=self._prompt.title), t("delete"), danger=True):
            return
        pid = self._prompt.id
        try:
            PromptService.delete(pid)
        except DatabaseError:
            return show_error(self, t("db_error"))
        toast(self, t("deleted_ok"))
        self.deleted.emit(pid)

    def _on_fav(self, on: bool) -> None:
        self._update_fav_icon()
        if self._prompt and not self._loading:
            try:
                PromptService.set_favorite(self._prompt.id, on)
                self._prompt.is_favorite = on
                self.favoriteChanged.emit(self._prompt.id, on)
            except DatabaseError:
                show_error(self, t("db_error"))

    def _on_archive(self) -> None:
        if not self._prompt or (self._dirty and not self.save()):
            return
        new = not self._prompt.is_archived
        try:
            PromptService.set_archived(self._prompt.id, new)
        except DatabaseError:
            return show_error(self, t("db_error"))
        self._prompt.is_archived = new
        self._update_arch_icon()
        toast(self, t("archived_ok" if new else "unarchived_ok"))
        self.archivedChanged.emit(self._prompt.id)

    def _update_fav_icon(self) -> None:
        on = self.fav_btn.isChecked()
        self.fav_btn.setIcon(icon("mdi6.star" if on else "mdi6.star-outline", self._pal["accent"] if on else None))

    def _update_arch_icon(self) -> None:
        arch = bool(self._prompt and self._prompt.is_archived)
        self.arch_btn.setIcon(icon("mdi6.archive-arrow-up-outline" if arch else "mdi6.archive-outline"))
        self.arch_btn.setToolTip(t("unarchive" if arch else "archive"))

    def _export(self, fmt: str) -> None:
        if not self._prompt or (self._dirty and not self.save()):
            return
        flt = t("filter_md" if fmt == "md" else "filter_txt")
        name = "".join(ch for ch in self._prompt.title if ch not in '\\/:*?"<>|').strip() or "prompt"
        path, _ = QFileDialog.getSaveFileName(self, t("export"), f"{name}.{fmt}", flt)
        if path:
            try:
                IOService.export_text(path, [self._prompt], fmt)
                toast(self, t("export_done", n=num(1)))
            except OSError as exc:
                show_error(self, t("io_error", detail=str(exc)))
