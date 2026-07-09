"""Unikalność ID (dynaword): pole id_field musi być unikalne. Brak pola → pominięcie."""
from __future__ import annotations
from ..models import Issue
from ..registry import check


@check("uniqueid")
def run(ctx) -> list:
    idf = ctx.formatka.get("id_field", "id")
    seen = set()
    dups = []
    present = 0
    for rec in ctx.records:
        if idf not in rec:
            continue
        present += 1
        v = rec[idf]
        if v in seen:
            dups.append(v)
        else:
            seen.add(v)
    if present == 0:
        return [Issue("info", "uniqueid", "data", f"brak pola '{idf}' — pominięto")]
    if dups:
        ex = ", ".join(str(x) for x in dups[:3])
        return [Issue("error", "uniqueid", "data", f"zduplikowane '{idf}': {len(dups)} (np. {ex})")]
    return [Issue("info", "uniqueid", "data", f"'{idf}' unikalne ({present})")]
