"""Skan PII: national-ID (PESEL/NIP/REGON/dowód)=błąd (NIP/REGON z błędną sumą=ostrzeżenie), email/telefon=ostrzeżenie. Tekst nested-aware + metadane.
FAIL-LOUD: gdy formatka nie wyłuska tekstu, OSTRZEGA (nie udaje „czyste").

national-ID wykrywany DWUWARSTWOWO — precyzja + pokrycie, zmierzone FP-safe:
  1. keyword-adjacent: etykieta (PESEL|NIP|REGON|dowód osobisty), opcjonalnie do 2 łączników
     ("PESEL to X", "PESEL wynosi X", "PESEL: numer X"), i numer o długości właściwej dla typu:
     PESEL 11, NIP 10, REGON 14 albo 9 cyfr (spacje/myślniki w numerze ok; sąsiednia liczba nie jest doklejana).
     PESEL z etykietą = błąd niezależnie od sumy kontrolnej (łapie OCR-garbled numery, które checksum by zgubił).
     NIP/REGON z etykietą: suma poprawna = błąd, błędna = ostrzeżenie (daty i zakresy lat po "NIP jest ...").
     Kontekstowe wzmianki bez numeru ("podaj PESEL") NIE łapane (FP-safe).
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
# keyword-adjacent national-ID: etykieta + separatory + do 2 łączników (nr/numer/to/wynosi/jest) + numer typu
_LABEL_GAP = r"[\s:.\-]{0,4}(?:(?:nr|numer|to|wynosi|jest)\.?[\s:.\-]{0,4}){0,2}"


def _digits(n: int) -> str:
    """Dokładnie n cyfr (pojedyncze spacje/myślniki między nimi), bez sąsiedniej cyfry po obu stronach."""
    return rf"(?<!\d)(\d(?:[\s\-]?\d){{{n - 1}}})(?!\d)"


PESEL_LABELED = re.compile(rf"(?i)PESEL{_LABEL_GAP}{_digits(11)}")
NIP_LABELED = re.compile(rf"(?i)NIP{_LABEL_GAP}{_digits(10)}")
REGON_LABELED = re.compile(rf"(?i)REGON{_LABEL_GAP}(?:{_digits(14)}|{_digits(9)})")
DOWOD_LABELED = re.compile(rf"(?i)dow[o\u00f3]d\s+osobist\w*{_LABEL_GAP}(\d[\d\s\-]{{7,13}}\d)")
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


def _weighted_mod11(s: str, weights: tuple) -> int:
    return sum(int(c) * w for c, w in zip(s, weights)) % 11


def _nip_valid(s: str) -> bool:
    """NIP: wagi 6,5,7,2,3,4,5,6,7, suma mod 11 = cyfra kontrolna (wynik 10 = numer niepoprawny)."""
    return _weighted_mod11(s, (6, 5, 7, 2, 3, 4, 5, 6, 7)) == int(s[9])


def _regon_valid(s: str) -> bool:
    """REGON 9 (wagi 8,9,2,3,4,5,6,7) albo 14 cyfr (wagi 2,4,8,5,0,9,7,3,6,1,2,4,8); suma mod 11 mod 10."""
    weights = (8, 9, 2, 3, 4, 5, 6, 7) if len(s) == 9 else (2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 2, 4, 8)
    return _weighted_mod11(s, weights) % 10 == int(s[-1])


def _labeled_ids(text: str) -> tuple[int, int]:
    """(błędy, ostrzeżenia) z warstwy keyword-adjacent."""
    errors = len(PESEL_LABELED.findall(text)) + len(DOWOD_LABELED.findall(text))
    warnings = 0
    for valid, matches in ((_nip_valid, NIP_LABELED.findall(text)),
                           (_regon_valid, (a or b for a, b in REGON_LABELED.findall(text)))):
        for m in matches:
            if valid(re.sub(r"[\s\-]", "", m)):
                errors += 1
            else:
                warnings += 1
    return errors, warnings


@check("pii")
def run(ctx) -> list:
    n_email = n_phone = n_natid = n_natid_warn = n_pesel = 0
    tx = 0
    bases = text_bases(ctx.formatka)
    for rec in ctx.records:
        ts = texts(rec, ctx.formatka)
        tx += len(ts)
        blob = ts + [v for k, v in rec.items() if isinstance(v, str) and k not in bases]
        for v in blob:
            n_email += len(EMAIL.findall(v))
            n_phone += len(PHONE.findall(v))
            natid_errors, natid_warnings = _labeled_ids(v)
            n_natid += natid_errors
            n_natid_warn += natid_warnings
            n_pesel += sum(1 for m in BARE11.findall(v) if _pesel_valid(m))
    out = []
    if ctx.records and tx == 0:
        out.append(Issue("error", "pii", "data", "text_fields nie wyłuskało tekstu — skan PII NIE wykonany (blokada; napraw formatkę)"))
    n_id = n_natid + n_pesel
    if n_id:
        out.append(Issue("error", "pii", "data",
                         f"national-ID wykryty: {n_id} (oznaczone PESEL/NIP/REGON/dowód: {n_natid}, gołe PESEL checksum-valid: {n_pesel}) — zredaguj przed publikacją"))
    if n_natid_warn:
        out.append(Issue("warn", "pii", "data",
                         f"NIP/REGON oznaczone, ale z błędną sumą kontrolną: {n_natid_warn} — sprawdź (data/zakres lat albo przekręcony numer)"))
    if n_email:
        out.append(Issue("warn", "pii", "data", f"emaile: {n_email} — rozważ redakcję"))
    if n_phone:
        out.append(Issue("warn", "pii", "data", f"potencjalne telefony: {n_phone}"))
    if tx > 0 and not (n_id or n_natid_warn or n_email or n_phone):
        out.append(Issue("info", "pii", "data", "PII czyste (tekst)"))
    return out
