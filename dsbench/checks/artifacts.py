"""Skan artefaktów tekstowych ekstrakcji/czyszczenia. Tekst brany z formatki (nested-aware).

Empiria 2026-08-06 (Arek-findings + team-QA na polish-dynaword): klasy które pipeline
czyści — ten check NIEZALEŻNIE weryfikuje na output (inny code-path łapie też bugi cleanera).

Dwie klasy wg dyscypliny FP:
  ENCODING (błąd — obecność = zawsze defekt, zero-FP):
    - U+FFFD (�)              — niedekodowalny bajt (decode-failure marker); nigdy nie treść.
    - Latin-2 mojibake        — ISO-8859-2-jako-Latin-1: ¶=ś ±=ą ³=ł ¼=ź ¿=ż MID-WORD.
                                Tylko ¶±³¼¿ (never-letters); æêñ WYKLUCZONE (legit obce, np. norw. "Næringsliv").
  STRUKTURALNE (ostrzeżenie — FP-prone, mieszają defekt z legit):
    - mid-word '?'            — charset-artefakt (ł/ś→?) + sentence-boundary-bez-spacji mix.
    - orphan leading-dash     — '^-\\n' resztka listy; NIE dialogowa pauza '- <słowo>'.
    - orphan page-number      — pierwsza linia = same cyfry, lub 'Strona X z Y'.
"""
from __future__ import annotations
import re
from ..models import Issue
from ..registry import check
from ..textextract import texts

_PL = "a-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ"
FFFD = "\ufffd"
_MOJI = "±³¶¼¿"                                              # never-letter Latin-2 mojibake (NIE æêñ)
MOJI_MID = re.compile(rf"[{_PL}][{re.escape(_MOJI)}][{_PL}]")
MIDQ = re.compile(rf"[{_PL}0-9]\?[{_PL}]")                   # FP-prone: charset-artefakt + brak spacji po '?'
ORPHAN_DASH = re.compile(r"^\s*-\s*\n")                      # goły '-' + newline (NIE dialog '- słowo')
PAGENUM = re.compile(r"^\s*\d+\s*\n|Strona\s+\d+\s+z\s+\d+", re.IGNORECASE)


@check("artifacts")
def run(ctx) -> list:
    n_fffd = n_moji = n_midq = n_dash = n_page = 0
    tx = 0
    for rec in ctx.records:
        for v in texts(rec, ctx.formatka):
            tx += 1
            n_fffd += v.count(FFFD)
            if MOJI_MID.search(v):
                n_moji += 1
            if MIDQ.search(v):
                n_midq += 1
            if ORPHAN_DASH.match(v):
                n_dash += 1
            if PAGENUM.match(v) or (v and PAGENUM.search(v[:40])):
                n_page += 1
    out = []
    if ctx.records and tx == 0:
        out.append(Issue("warn", "artifacts", "data", "text_fields nie wyłuskało tekstu — skan artefaktów pominięty"))
        return out
    if n_fffd:
        out.append(Issue("error", "artifacts", "data", f"U+FFFD (�) niedekodowalne bajty: {n_fffd} wystąpień — drop/re-extract"))
    if n_moji:
        out.append(Issue("error", "artifacts", "data", f"Latin-2 mojibake (¶±³¼¿ mid-word): {n_moji} rec — recoverable-remap ¶→ś ±→ą ³→ł ¼→ź ¿→ż"))
    if n_midq:
        out.append(Issue("warn", "artifacts", "data", f"mid-word '?': {n_midq} rec (FP-prone: charset-artefakt + sentence-boundary; osądź próbką)"))
    if n_dash:
        out.append(Issue("warn", "artifacts", "data", f"orphan leading-dash '-\\n': {n_dash} rec (resztka listy; NIE dialog '- słowo')"))
    if n_page:
        out.append(Issue("warn", "artifacts", "data", f"orphan page-number / 'Strona X z Y': {n_page} rec (paginacja-residue)"))
    if tx > 0 and not (n_fffd or n_moji or n_midq or n_dash or n_page):
        out.append(Issue("info", "artifacts", "data", "artefakty tekstowe czyste"))
    return out
