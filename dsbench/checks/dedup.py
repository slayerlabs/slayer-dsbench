"""Duplikaty dokładne (hash całego rekordu). >0 = błąd bramki."""
from __future__ import annotations
import hashlib
import json
from ..models import Issue
from ..registry import check


@check("dedup")
def run(ctx) -> list:
    seen = set()
    dups = 0
    for rec in ctx.records:
        h = hashlib.sha1(json.dumps(rec, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        if h in seen:
            dups += 1
        else:
            seen.add(h)
    if dups:
        return [Issue("error", "dedup", "data", f"duplikaty rekordów: {dups}")]
    return [Issue("info", "dedup", "data", "duplikaty: 0")]
