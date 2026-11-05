"""Prompt variable helpers: {{topic}}, {{language}}, {{role}} ..."""
from __future__ import annotations

import re
import unicodedata

VAR_RE = re.compile(r"\{\{\s*([^\s{}][^{}]*?)\s*\}\}")
STANDARD_VARIABLES = ("topic", "language", "role", "context", "output_format")


def find_variables(text: str) -> list[str]:
    """Unique variable names in order of first appearance."""
    seen: dict[str, None] = {}
    for m in VAR_RE.finditer(text or ""):
        seen.setdefault(m.group(1), None)
    return list(seen)


def fill_variables(text: str, values: dict[str, str]) -> str:
    """Replace variables that have a non-empty value; leave the others untouched."""
    def repl(m: re.Match[str]) -> str:
        v = values.get(m.group(1), "")
        return v if v else m.group(0)
    return VAR_RE.sub(repl, text or "")


def line_direction(line: str) -> str:
    """'rtl' or 'ltr' from the first strong character of a line."""
    for ch in line:
        d = unicodedata.bidirectional(ch)
        if d == "L":
            return "ltr"
        if d in ("R", "AL"):
            return "rtl"
    return "ltr"
