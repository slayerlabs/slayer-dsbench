"""Skan PII: PESEL=błąd, email/telefon=ostrzeżenie. Tekst nested-aware + metadane.
FAIL-LOUD: gdy formatka nie wyłuska tekstu, OSTRZEGA (nie udaje „czyste")."""
from __future__ import annotations
import re
from ..models import Issue
from ..registry import check
from ..textextract import texts, text_bases

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PESEL = re.compile(r"(?<!\d)\d{11}(?!\d)")
PHONE = re.compile(r"(?<!\d)(?:\+48[\s-]?)?(?:\d[\s-]?){8}\d(?!\d)")


@check("pii")
def run(ctx) -> list:
    n_email = n_pesel = n_phone = 0
    tx = 0
    bases = text_bases(ctx.formatka)
    for rec in ctx.records:
        ts = texts(rec, ctx.formatka)
        tx += len(ts)
        blob = ts + [v for k, v in rec.items() if isinstance(v, str) and k not in bases]
        for v in blob:
            n_email += len(EMAIL.findall(v))
            n_pesel += len(PESEL.findall(v))
            n_phone += len(PHONE.findall(v))
    out = []
    if ctx.records and tx == 0:
        out.append(Issue("error", "pii", "data", "text_fields nie wyłuskało tekstu — skan PII NIE wykonany (blokada; napraw formatkę)"))
    if n_pesel:
        out.append(Issue("error", "pii", "data", f"PESEL wykryty: {n_pesel} — zredaguj przed publikacją"))
    if n_email:
        out.append(Issue("warn", "pii", "data", f"emaile: {n_email} — rozważ redakcję"))
    if n_phone:
        out.append(Issue("warn", "pii", "data", f"potencjalne telefony: {n_phone}"))
    if tx > 0 and not (n_pesel or n_email or n_phone):
        out.append(Issue("info", "pii", "data", "PII czyste (tekst)"))
    return out
