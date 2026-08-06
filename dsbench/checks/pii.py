"""Skan PII: national-ID (PESEL/NIP/REGON/dowód)=błąd, email/telefon=ostrzeżenie. Tekst nested-aware + metadane.
FAIL-LOUD: gdy formatka nie wyłuska tekstu, OSTRZEGA (nie udaje „czyste").

national-ID (błąd) wykrywany DWUWARSTWOWO — precyzja + pokrycie, zmierzone FP-safe:
  1. keyword-adjacent: (PESEL|NIP|REGON|dowód osobisty) + PRZYLEGAJĄCY 9-13-cyfrowy numer.
     Łapie też OCR-garbled numery (checksum by je zgubił) i NIP/REGON/dowód. Kontekstowe
     wzmianki bez numeru ("podaj PESEL") NIE łapane (FP-safe).
  2. gołe 11 cyfr walidowane checksumem+datą PESEL — łapie NIEoznaczone PESELe, a kasuje
     śmieci (URLe/kody-produktów/nr-polis: 93/95 gołych-11-cyfr na realnym korpusie to FP,
     checksum je odrzuca; naiwne \\d{11} dawało 95 fałszywych trafień)."""
from __future__ import annotations
import re
from ..models import Issue
from ..registry import check
from ..textextract import texts, text_bases

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?<!\d)(?:\+48[\s-]?)?(?:\d[\s-]?){8}\d(?!\d)")
# keyword-adjacent national-ID: etykieta + przylegający 9-13-cyfrowy numer (spacje/myślniki ok)
NATID = re.compile(r"(?i)(PESEL|NIP|REGON|dow[o\u00f3]d\s+osobist\w*)([\s:.\-]{0,4}(?:nr\.?|numer)?[\s:.\-]{0,4})(\d[\d\s\-]{7,13}\d)")
# goły kandydat PESEL (11 cyfr) — walidowany checksumem+datą (patrz _pesel_valid), kasuje FP
BARE11 = re.compile(r"(?<!\d)\d{11}(?!\d)")
_W = (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)


def _pesel_valid(s: str) -> bool:
    """PESEL: 11 cyfr, checksum (ważona mod-10) + poprawna data (miesiąc z offsetem-wieku, dzień)."""
    if len(s) != 11 or not s.isdigit():
        return False
    if (10 - sum(int(s[i]) * _W[i] for i in range(10)) % 10) % 10 != int(s[10]):
        return False
    mm = int(s[2:4]) % 20  # 01-12/21-32/41-52/61-72/81-92 → wiek; %20 mapuje na 1-12
    return 1 <= mm <= 12 and 1 <= int(s[4:6]) <= 31


@check("pii")
def run(ctx) -> list:
    n_email = n_phone = n_natid = n_pesel = 0
    tx = 0
    bases = text_bases(ctx.formatka)
    for rec in ctx.records:
        ts = texts(rec, ctx.formatka)
        tx += len(ts)
        blob = ts + [v for k, v in rec.items() if isinstance(v, str) and k not in bases]
        for v in blob:
            n_email += len(EMAIL.findall(v))
            n_phone += len(PHONE.findall(v))
            n_natid += len(NATID.findall(v))
            n_pesel += sum(1 for m in BARE11.findall(v) if _pesel_valid(m))
    out = []
    if ctx.records and tx == 0:
        out.append(Issue("error", "pii", "data", "text_fields nie wyłuskało tekstu — skan PII NIE wykonany (blokada; napraw formatkę)"))
    n_id = n_natid + n_pesel
    if n_id:
        out.append(Issue("error", "pii", "data",
                         f"national-ID wykryty: {n_id} (oznaczone PESEL/NIP/REGON/dowód: {n_natid}, gołe PESEL checksum-valid: {n_pesel}) — zredaguj przed publikacją"))
    if n_email:
        out.append(Issue("warn", "pii", "data", f"emaile: {n_email} — rozważ redakcję"))
    if n_phone:
        out.append(Issue("warn", "pii", "data", f"potencjalne telefony: {n_phone}"))
    if tx > 0 and not (n_id or n_email or n_phone):
        out.append(Issue("info", "pii", "data", "PII czyste (tekst)"))
    return out
