from __future__ import annotations

import json
import logging
from typing import Any

from app.utils.paths import settings_path

log = logging.getLogger(__name__)

DEFAULTS: dict[str, Any] = {
    "language": "fa", "theme": "oled", "font_size": 13,
    "startup": "dashboard", "last_page": "dashboard", "geometry": "",
}
CHOICES = {
    "language": ("fa", "en"), "theme": ("oled", "charcoal", "light"),
    "startup": ("dashboard", "prompts", "last"),
}
FONT_SIZES = tuple(range(11, 19))


class Settings:
    def __init__(self) -> None:
        self._data = dict(DEFAULTS)
        try:
            raw = json.loads(settings_path().read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for k, v in raw.items():
                    if k in DEFAULTS and self._valid(k, v):
                        self._data[k] = v
        except (OSError, ValueError):
            pass

    @staticmethod
    def _valid(key: str, value: Any) -> bool:
        if key in CHOICES:
            return value in CHOICES[key]
        if key == "font_size":
            return value in FONT_SIZES
        return isinstance(value, type(DEFAULTS[key]))

    def get(self, key: str) -> Any:
        return self._data[key]

    def set(self, key: str, value: Any) -> None:
        if key not in DEFAULTS or not self._valid(key, value):
            raise ValueError(f"invalid setting {key}={value!r}")
        self._data[key] = value
        self.save()

    def save(self) -> None:
        try:
            tmp = settings_path().with_suffix(".tmp")
            tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(settings_path())
        except OSError:
            log.exception("Could not save settings")
