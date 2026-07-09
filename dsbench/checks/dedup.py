"""Duplikaty TREŚCI (nested-aware): hash wyłuskanego tekstu (fallback: cały rekord). >0 = błąd."""
from __future__ import annotations
import hashlib
import json
from ..models import Issue
from ..registry import check
from ..textextract import texts


@check("dedup")
def run(ctx) -> list:
    seen = set()
    dups = 0
    for rec in ctx.records:
        ts = texts(rec, ctx.formatka)
        key = "\u0001".join(ts) if ts else json.dumps(rec, sort_keys=True, ensure_ascii=False)
        h = hashlib.sha1(key.encode("utf-8")).hexdigest()
        if h in seen:
            dups += 1
        else:
            seen.add(h)
    if dups:
        return [Issue("error", "dedup", "data", f"duplikaty treści: {dups}")]
    return [Issue("info", "dedup", "data", "duplikaty: 0")]
