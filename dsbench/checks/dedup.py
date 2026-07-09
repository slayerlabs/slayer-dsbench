"""Duplikaty TREŚCI (dynaword): hash pola tekstowego (fallback: cały rekord). >0 = błąd bramki."""
from __future__ import annotations
import hashlib
import json
from ..models import Issue
from ..registry import check


@check("dedup")
def run(ctx) -> list:
    tf = ctx.formatka.get("text_field", "text")
    seen = set()
    dups = 0
    for rec in ctx.records:
        val = rec.get(tf)
        key = val if isinstance(val, str) else json.dumps(rec, sort_keys=True, ensure_ascii=False)
        h = hashlib.sha1(key.encode("utf-8")).hexdigest()
        if h in seen:
            dups += 1
        else:
            seen.add(h)
    if dups:
        return [Issue("error", "dedup", "data", f"duplikaty treści ('{tf}'): {dups}")]
    return [Issue("info", "dedup", "data", "duplikaty: 0")]
