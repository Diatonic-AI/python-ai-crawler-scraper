#!/usr/bin/env python3
"""
Markdown linter/formatter using mdformat (opinionated).
Returns formatted markdown and a list of simple rule notes (non-blocking).
"""
from __future__ import annotations

from typing import List, Tuple

try:
    import mdformat  # type: ignore
except Exception:  # pragma: no cover
    mdformat = None  # type: ignore


def lint_and_format(markdown: str) -> Tuple[str, List[str]]:
    notes: List[str] = []
    out = markdown
    if mdformat is not None:
        try:
            out = mdformat.text(markdown)
        except Exception as e:  # pragma: no cover
            notes.append(f"mdformat error: {e}")
    # trivial checks
    if not markdown.strip().startswith("#"):
        notes.append("no top-level heading detected")
    return out, notes
