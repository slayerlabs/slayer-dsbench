"""Puste teksty (nested-aware): rekord bez tekstu lub z pustym/białym tekstem = błąd."""
from __future__ import annotations
from ..models import Issue
from ..registry import check
from ..textextract import texts


@check("empty")
def run(ctx) -> list:
    empt = 0
    for rec in ctx.records:
        ts = texts(rec, ctx.formatka)
        if not ts or any((not isinstance(t, str)) or (not t.strip()) for t in ts):
            empt += 1
    if empt:
        return [Issue("error", "empty", "data", f"puste/brak tekstu: {empt} rekord(ów)")]
    return [Issue("info", "empty", "data", "brak pustych tekstów")]
