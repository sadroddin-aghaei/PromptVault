"""Icon helpers (QtAwesome / Material Design Icons) and the programmatic app icon."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPainterPath, QPen, QPixmap

try:
    import qtawesome as qta
except Exception:  # pragma: no cover - optional dependency fallback
    qta = None

_color = "#f4f4f5"
_muted = "#8d8d96"


def set_icon_colors(color: str, muted: str) -> None:
    global _color, _muted
    _color, _muted = color, muted


def icon(name: str, color: str | None = None) -> QIcon:
    if qta is None:
        return QIcon()
    try:
        return qta.icon(name, color=color or _color, color_disabled=_muted)
    except Exception:
        return QIcon()


def draw_logo(size: int = 256) -> QImage:
    """Minimal prompt/document mark: rounded black tile, red page with a '>_' prompt."""
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    s = size / 256
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#0b0b0d"))
    p.drawRoundedRect(QRectF(8 * s, 8 * s, 240 * s, 240 * s), 56 * s, 56 * s)
    p.setPen(QPen(QColor("#26262a"), 3 * s))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(9.5 * s, 9.5 * s, 237 * s, 237 * s), 55 * s, 55 * s)
    page = QPainterPath()
    page.moveTo(78 * s, 58 * s)
    page.lineTo(154 * s, 58 * s)
    page.lineTo(186 * s, 90 * s)
    page.lineTo(186 * s, 198 * s)
    page.quadTo(186 * s, 206 * s, 178 * s, 206 * s)
    page.lineTo(78 * s, 206 * s)
    page.quadTo(70 * s, 206 * s, 70 * s, 198 * s)
    page.lineTo(70 * s, 66 * s)
    page.quadTo(70 * s, 58 * s, 78 * s, 58 * s)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#e5383b"))
    p.drawPath(page)
    p.setBrush(QColor(0, 0, 0, 70))
    fold = QPainterPath()
    fold.moveTo(154 * s, 58 * s)
    fold.lineTo(154 * s, 82 * s)
    fold.quadTo(154 * s, 90 * s, 162 * s, 90 * s)
    fold.lineTo(186 * s, 90 * s)
    fold.closeSubpath()
    p.drawPath(fold)
    pen = QPen(QColor("#ffffff"), 13 * s)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.drawPolyline([QPointF(96 * s, 128 * s), QPointF(116 * s, 146 * s), QPointF(96 * s, 164 * s)])
    p.drawLine(QPointF(128 * s, 168 * s), QPointF(158 * s, 168 * s))
    p.end()
    return img


def app_icon() -> QIcon:
    ic = QIcon()
    for sz in (16, 24, 32, 48, 64, 128, 256):
        ic.addPixmap(QPixmap.fromImage(draw_logo(sz)))
    return ic


def logo_pixmap(size: int) -> QPixmap:
    return QPixmap.fromImage(draw_logo(size * 2)).scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
