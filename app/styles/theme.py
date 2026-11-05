"""Design tokens and the QSS stylesheet (OLED black / charcoal / light, red accent)."""
from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen

from app.utils.paths import cache_dir

PALETTES: dict[str, dict[str, str]] = {
    "oled": dict(bg="#000000", surface="#08080a", card="#101012", elevated="#18181b", border="#26262a",
                 border_hover="#3a3a40", text="#f4f4f5", muted="#8d8d96", accent="#e5383b", accent_hover="#f0494c",
                 accent_press="#c92d30", accent_soft="rgba(229,56,59,38)", on_accent="#ffffff", danger="#ff5a5f",
                 selection="rgba(229,56,59,60)", shadow="#000000"),
    "charcoal": dict(bg="#131315", surface="#18181b", card="#1f1f23", elevated="#28282d", border="#303036",
                     border_hover="#45454d", text="#f2f2f3", muted="#9a9aa3", accent="#e5383b", accent_hover="#f0494c",
                     accent_press="#c92d30", accent_soft="rgba(229,56,59,38)", on_accent="#ffffff", danger="#ff5a5f",
                     selection="rgba(229,56,59,60)", shadow="#000000"),
    "light": dict(bg="#f5f5f6", surface="#ffffff", card="#ffffff", elevated="#f0f0f2", border="#e3e3e7",
                  border_hover="#c9c9d0", text="#18181b", muted="#6f6f7a", accent="#d62828", accent_hover="#e03a3a",
                  accent_press="#b82020", accent_soft="rgba(214,40,40,30)", on_accent="#ffffff", danger="#d62828",
                  selection="rgba(214,40,40,50)", shadow="#a0a0b0"),
}
FONT_STACK = '"Vazirmatn", "Segoe UI", "Inter", "Tahoma", "Noto Sans Arabic", sans-serif'
MONO_STACK = '"Cascadia Mono", "Consolas", "Menlo", "DejaVu Sans Mono", monospace'


def palette(theme: str) -> dict[str, str]:
    return PALETTES.get(theme, PALETTES["oled"])


def _chevron(color: str) -> str:
    path = cache_dir() / f"chevron-{color.lstrip('#')}.png"
    if not path.exists():
        img = QImage(24, 24, QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(color), 2.2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.drawPolyline([QPointF(7, 9.5), QPointF(12, 14.5), QPointF(17, 9.5)])
        p.end()
        img.save(str(path))
    return path.as_posix()


def build_qss(theme: str, font_size: int, rtl: bool) -> str:
    c = palette(theme)
    nav_align = "right" if rtl else "left"
    return f"""
* {{ font-family: {FONT_STACK}; font-size: {font_size}px; outline: 0; }}
QWidget {{ color: {c['text']}; }}
QMainWindow, QDialog, QMessageBox {{ background: {c['bg']}; }}
#Root, #Page {{ background: {c['bg']}; }}
QToolTip {{ background: {c['elevated']}; color: {c['text']}; border: 1px solid {c['border']}; padding: 5px 8px; border-radius: 6px; }}

#Sidebar {{ background: {c['surface']}; }}
#Logo {{ font-size: {font_size + 3}px; font-weight: 700; letter-spacing: 0.3px; }}
#Tagline, #Muted, #Footer {{ color: {c['muted']}; }}
#Footer {{ font-size: {max(10, font_size - 2)}px; padding: 7px; background: {c['surface']}; }}
#PageTitle {{ font-size: {font_size + 9}px; font-weight: 700; }}
#PageSubtitle {{ color: {c['muted']}; }}
#SectionTitle {{ font-size: {font_size + 1}px; font-weight: 600; }}
#StatValue {{ font-size: {font_size + 15}px; font-weight: 700; }}
#UnsavedBadge {{ color: {c['accent']}; font-weight: 600; }}
#SavedBadge {{ color: {c['muted']}; }}

QPushButton[nav="true"] {{ background: transparent; border: none; border-radius: 10px; padding: 10px 14px;
    text-align: {nav_align}; color: {c['muted']}; font-weight: 500; }}
QPushButton[nav="true"]:hover {{ background: {c['elevated']}; color: {c['text']}; }}
QPushButton[nav="true"]:checked {{ background: {c['accent_soft']}; color: {c['text']}; font-weight: 600; }}

QPushButton {{ background: {c['elevated']}; border: 1px solid {c['border']}; border-radius: 9px; padding: 7px 14px; font-weight: 500; }}
QPushButton:hover {{ border-color: {c['border_hover']}; }}
QPushButton:pressed {{ background: {c['card']}; }}
QPushButton:disabled {{ color: {c['muted']}; background: {c['card']}; border-color: {c['border']}; }}
QPushButton:checked[variant="toggle"] {{ background: {c['accent_soft']}; border-color: {c['accent']}; }}
QPushButton[variant="primary"] {{ background: {c['accent']}; border: 1px solid {c['accent']}; color: {c['on_accent']}; font-weight: 600; }}
QPushButton[variant="primary"]:hover {{ background: {c['accent_hover']}; border-color: {c['accent_hover']}; }}
QPushButton[variant="primary"]:pressed {{ background: {c['accent_press']}; }}
QPushButton[variant="primary"]:disabled {{ background: {c['elevated']}; border-color: {c['border']}; color: {c['muted']}; }}
QPushButton[variant="ghost"] {{ background: transparent; border: 1px solid transparent; }}
QPushButton[variant="ghost"]:hover {{ background: {c['elevated']}; }}
QPushButton[variant="danger"] {{ color: {c['danger']}; }}
QPushButton[variant="danger"]:hover {{ border-color: {c['danger']}; }}
QToolButton {{ background: transparent; border: none; border-radius: 8px; padding: 5px; }}
QToolButton:hover {{ background: {c['elevated']}; }}
QToolButton::menu-indicator {{ image: none; }}

QLineEdit, QPlainTextEdit, QTextBrowser, QComboBox {{ background: {c['card']}; border: 1px solid {c['border']};
    border-radius: 9px; padding: 8px 11px; selection-background-color: {c['selection']}; selection-color: {c['text']}; }}
QLineEdit:hover, QComboBox:hover, QPlainTextEdit:hover {{ border-color: {c['border_hover']}; }}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{ border-color: {c['accent']}; }}
QLineEdit#TitleEdit {{ background: transparent; border: 1px solid transparent; font-size: {font_size + 6}px; font-weight: 700; padding: 4px 6px; }}
QLineEdit#TitleEdit:hover {{ border-color: {c['border']}; }}
QLineEdit#TitleEdit:focus {{ border-color: {c['accent']}; background: {c['card']}; }}
QPlainTextEdit {{ padding: 12px; }}
QTextBrowser {{ padding: 12px; background: {c['surface']}; }}
QComboBox {{ padding: 7px 11px; padding-right: 28px; padding-left: 11px; }}
QComboBox::drop-down {{ border: none; width: 26px; subcontrol-origin: padding; subcontrol-position: center right; }}
QComboBox::down-arrow {{ image: url({_chevron(c['muted'])}); width: 14px; height: 14px; }}
QComboBox QAbstractItemView {{ background: {c['elevated']}; border: 1px solid {c['border']}; border-radius: 8px; padding: 4px;
    selection-background-color: {c['accent_soft']}; selection-color: {c['text']}; outline: 0; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 5px; border: 1px solid {c['border_hover']}; background: {c['card']}; }}
QCheckBox::indicator:checked {{ background: {c['accent']}; border-color: {c['accent']}; }}

QFrame[card="true"] {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 14px; }}
QFrame[card="true"][hoverable="true"]:hover {{ border-color: {c['border_hover']}; }}
QFrame[card="true"][selected="true"] {{ border-color: {c['accent']}; background: {c['elevated']}; }}
QFrame[card="true"] QLabel, QFrame[card="true"] QCheckBox {{ background: transparent; border: none; }}
QFrame[row="true"] {{ background: transparent; border: 1px solid transparent; border-radius: 10px; }}
QFrame[row="true"]:hover {{ background: {c['elevated']}; }}
QFrame[row="true"] QLabel {{ background: transparent; }}
#Chip {{ background: {c['elevated']}; border-radius: 8px; padding: 2px 8px; color: {c['muted']}; font-size: {max(10, font_size - 2)}px; }}
#ChipAccent {{ background: {c['accent_soft']}; border-radius: 8px; padding: 2px 8px; color: {c['text']}; font-size: {max(10, font_size - 2)}px; }}
#Toast {{ background: {c['elevated']}; color: {c['text']}; border: 1px solid {c['border_hover']}; border-radius: 12px; padding: 10px 18px; font-weight: 500; }}
#VarPanel {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 12px; }}
#VarPanel QLabel {{ background: transparent; }}

QListWidget {{ background: transparent; border: none; }}
QListWidget::item {{ background: transparent; border: none; }}
QListWidget::item:selected, QListWidget::item:hover {{ background: transparent; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 4px; min-height: 32px; }}
QScrollBar::handle:vertical:hover {{ background: {c['border_hover']}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {c['border']}; border-radius: 4px; min-width: 32px; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ background: none; border: none; width: 0; height: 0; }}
QSplitter::handle {{ background: transparent; }}
QProgressBar {{ background: {c['elevated']}; border: none; border-radius: 2px; max-height: 4px; min-height: 4px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ background: {c['accent']}; border-radius: 2px; }}
QMenu {{ background: {c['elevated']}; border: 1px solid {c['border']}; border-radius: 10px; padding: 6px; }}
QMenu::item {{ padding: 7px 18px; border-radius: 6px; }}
QMenu::item:selected {{ background: {c['accent_soft']}; }}
QMenu::separator {{ height: 1px; background: {c['border']}; margin: 5px 8px; }}
QMessageBox QLabel {{ color: {c['text']}; }}
"""
