"""Statystyki próbki (info, nigdy nie failuje). Tekst nested-aware (text_fields)."""
from __future__ import annotations
from ..models import Issue
from ..registry import check
from ..textextract import texts


@check("stats")
def run(ctx) -> list:
    n = len(ctx.records)
    chars = words = 0
    for rec in ctx.records:
        for t in texts(rec, ctx.formatka):
            chars += len(t)
            words += len(t.split())
    avg = round(words / n, 1) if n else 0
    return [Issue("info", "stats", "data", f"rekordy={n} znaki={chars} słowa={words} śr.słów/rek={avg} (próbka)")]
