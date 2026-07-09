"""Skan PII na próbce: PESEL = błąd (wrażliwe), email/telefon = ostrzeżenie. Skanuje wszystkie pola tekstowe."""
from __future__ import annotations
import re
from ..models import Issue
from ..registry import check

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PESEL = re.compile(r"(?<!\d)\d{11}(?!\d)")
PHONE = re.compile(r"(?<!\d)(?:\+48[\s-]?)?(?:\d[\s-]?){8}\d(?!\d)")


@check("pii")
def run(ctx) -> list:
    n_email = n_pesel = n_phone = 0
    for rec in ctx.records:
        for v in rec.values():
            if not isinstance(v, str):
                continue
            n_email += len(EMAIL.findall(v))
            n_pesel += len(PESEL.findall(v))
            n_phone += len(PHONE.findall(v))
    out = []
    if n_pesel:
        out.append(Issue("error", "pii", "data", f"PESEL wykryty: {n_pesel} — zredaguj przed publikacją"))
    if n_email:
        out.append(Issue("warn", "pii", "data", f"emaile: {n_email} — rozważ redakcję"))
    if n_phone:
        out.append(Issue("warn", "pii", "data", f"potencjalne telefony: {n_phone}"))
    if not (n_pesel or n_email or n_phone):
        out.append(Issue("info", "pii", "data", "PII czyste (próbka)"))
    return out
