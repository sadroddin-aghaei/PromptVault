"""Regenerate assets/icons/promptvault.png/.ico from the programmatic logo."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtGui import QGuiApplication

from app.ui.components.icons import draw_logo

app = QGuiApplication([])
out = Path(__file__).resolve().parents[1] / "assets" / "icons"
img = draw_logo(256)
img.save(str(out / "promptvault.png"))
img.save(str(out / "promptvault.ico"))
draw_logo(1024).save(str(out / "promptvault-1024.png"))  # source for the macOS .icns
print("icons written to", out)
