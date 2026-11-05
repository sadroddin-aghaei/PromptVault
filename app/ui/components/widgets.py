"""Reusable building blocks: buttons, cards, elided labels, dialogs, toast."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (QFrame, QGraphicsDropShadowEffect, QLabel, QMessageBox, QPushButton, QSizePolicy,
                               QStyle, QVBoxLayout, QWidget)

from app.ui.components.icons import icon
from app.utils.i18n import t


def make_button(text: str = "", icon_name: str | None = None, variant: str = "default",
                tooltip: str | None = None, checkable: bool = False) -> QPushButton:
    b = QPushButton(text)
    b.setProperty("variant", "toggle" if checkable and variant == "default" else variant)
    b.setCursor(Qt.PointingHandCursor)
    b.setCheckable(checkable)
    if icon_name:
        b.setIcon(icon(icon_name, "#ffffff" if variant == "primary" else None))
        b.setIconSize(QSize(16, 16))
    if tooltip:
        b.setToolTip(tooltip)
    return b


def repolish(w: QWidget) -> None:
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()


def label(text: str = "", name: str | None = None, wrap: bool = False) -> QLabel:
    lb = QLabel(text)
    if name:
        lb.setObjectName(name)
    lb.setWordWrap(wrap)
    return lb


class Card(QFrame):
    def __init__(self, hoverable: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("card", True)
        self.setProperty("hoverable", hoverable)


def add_shadow(w: QWidget, blur: int = 28, alpha: int = 90) -> None:
    from PySide6.QtGui import QColor
    fx = QGraphicsDropShadowEffect(w)
    fx.setBlurRadius(blur)
    fx.setOffset(0, 6)
    fx.setColor(QColor(0, 0, 0, alpha))
    w.setGraphicsEffect(fx)


class ClickableFrame(QFrame):
    clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(e)


class ElidedLabel(QLabel):
    """Single-line label that elides instead of forcing the layout wider."""

    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

    def minimumSizeHint(self) -> QSize:
        return QSize(0, super().minimumSizeHint().height())

    def paintEvent(self, _e) -> None:
        from PySide6.QtGui import QPainter
        p = QPainter(self)
        txt = self.fontMetrics().elidedText(self.text(), Qt.ElideRight, self.width())
        flags = QStyle.visualAlignment(self.layoutDirection(), Qt.AlignLeading | Qt.AlignVCenter)
        self.style().drawItemText(p, self.rect(), int(flags), self.palette(), self.isEnabled(), txt, QPalette.WindowText)


class PageHeader(QWidget):
    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lay.addWidget(label(title, "PageTitle"))
        if subtitle:
            lay.addWidget(label(subtitle, "PageSubtitle"))


class Toast(QLabel):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setAlignment(Qt.AlignCenter)
        self.hide()
        self._timer = QTimer(self, singleShot=True, interval=1900)
        self._timer.timeout.connect(self.hide)

    def popup(self, text: str) -> None:
        self.setText(text)
        self.adjustSize()
        par = self.parentWidget()
        self.move(QPoint((par.width() - self.width()) // 2, par.height() - self.height() - 56))
        self.raise_()
        self.show()
        self._timer.start()


def toast(widget: QWidget, text: str) -> None:
    win = widget.window()
    if hasattr(win, "toast"):
        win.toast(text)


# ------------------------------------------------------------------ dialogs
def _box(parent, icon_kind, title, text) -> QMessageBox:
    box = QMessageBox(parent)
    box.setIcon(icon_kind)
    box.setWindowTitle(title)
    box.setText(text)
    return box


def confirm(parent, title: str, text: str, yes_text: str, danger: bool = False) -> bool:
    box = _box(parent, QMessageBox.Warning if danger else QMessageBox.Question, title, text)
    yes = box.addButton(yes_text, QMessageBox.AcceptRole)
    yes.setProperty("variant", "danger" if danger else "primary")
    no = box.addButton(t("cancel"), QMessageBox.RejectRole)
    box.setDefaultButton(no)
    box.exec()
    return box.clickedButton() is yes


def ask_unsaved(parent) -> str:
    """Returns 'save', 'discard' or 'cancel'."""
    box = _box(parent, QMessageBox.Question, t("unsaved_title"), t("unsaved_text"))
    save = box.addButton(t("save_changes"), QMessageBox.AcceptRole)
    save.setProperty("variant", "primary")
    discard = box.addButton(t("discard"), QMessageBox.DestructiveRole)
    cancel = box.addButton(t("cancel"), QMessageBox.RejectRole)
    box.setDefaultButton(save)
    box.exec()
    clicked = box.clickedButton()
    return "save" if clicked is save else "discard" if clicked is discard else "cancel"


def show_error(parent, text: str) -> None:
    box = _box(parent, QMessageBox.Critical, t("error"), text)
    box.addButton("OK", QMessageBox.AcceptRole)
    box.exec()


def show_info(parent, title: str, text: str) -> None:
    box = _box(parent, QMessageBox.Information, title, text)
    box.addButton("OK", QMessageBox.AcceptRole)
    box.exec()
