"""Puste teksty (dynaword): pole tekstowe nie może być puste/białe. Steruje formatka (text_field)."""
from __future__ import annotations
from ..models import Issue
from ..registry import check


@check("empty")
def run(ctx) -> list:
    tf = ctx.formatka.get("text_field", "text")
    empt = 0
    for rec in ctx.records:
        if tf in rec:
            v = rec[tf]
            if not isinstance(v, str) or not v.strip():
                empt += 1
    if empt:
        return [Issue("error", "empty", "data", f"puste pole '{tf}': {empt} rekord(ów)")]
    return [Issue("info", "empty", "data", f"brak pustych '{tf}'")]
