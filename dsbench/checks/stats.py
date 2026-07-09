"""Statystyki próbki (info, nigdy nie failuje). Pole tekstowe bierze z formatki (text_field)."""
from __future__ import annotations
from ..models import Issue
from ..registry import check


@check("stats")
def run(ctx) -> list:
    tf = ctx.formatka.get("text_field", "text")
    n = len(ctx.records)
    chars = words = 0
    for rec in ctx.records:
        t = rec.get(tf)
        if isinstance(t, str):
            chars += len(t)
            words += len(t.split())
    avg = round(words / n, 1) if n else 0
    return [Issue("info", "stats", "data", f"rekordy={n} znaki={chars} słowa={words} śr.słów/rek={avg} (próbka)")]
