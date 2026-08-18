"""Skan web-boilerplate: single-line comment/nav-cruft (blog/CMS) który przeżył blokowy frame_merge.

Luka odsłonięta przez trening GoLLeM-110M (2026-08-11): ~10% dok korpusu miało ≥1 marker
web-boilerplate → ~13% emisji modelu. frame_merge (doc-freq, bloki ≥3 linii) CELOWO zostawia
IZOLOWANE high-freq linie (FP-safe dla "Pozdrawiam/Witam" = conversational). Ten check łapie te
izolowane linie curated exact-blocklistą, z FP-tierem (markery + walidacja Wartownika, bateria FP):

  HARD (zero-FP, auto-strip-safe): comment/nav-cruft ~0 trafień w czystej prozie → warn (do strip).
  SOFT (FP-podatne, FLAG-only): bywają legalne w treści → info, NIGDY auto-strip.

FP-gate: markery HARD zwalidowane 0-na-czystej-prozie (wolne_lektury) PRZED promocją — jak
phone-regex-hardening. Falsyfikowalność bramki: scrub korpusu BEZ spadku emisji modelu = check
nie działa (nie ufamy samej korpus-metryce; emisja przed/po = domknięcie, mierzy eval).
"""
from __future__ import annotations
import re
from ..models import Issue
from ..registry import check
from ..textextract import texts

# normalizacja linii: lower + usuń całą spację (łapie "OdpowiedzUsuń" i "Odpowiedz Usuń")
_norm = lambda s: re.sub(r"\s+", "", s.strip().lower())

# HARD — comment/nav-cruft, zero-FP na prozie (Wartownik, bateria FP). Match: znormalizowana linia == marker.
HARD = {
    "odpowiedzusuń", "odpowiedzusun",
    "prześlijkomentarz", "przeslijkomentarz",
    "brakkomentarzy",
    "dodajkomentarz",
    "nowszypost", "starszypost",
    "komentarzedoposta", "komentarzedopostu",
}
# SOFT — FP-podatne (legalne w treści): tylko flaga, NIGDY auto-strip.
SOFT = {
    "regulamin", "czytajwięcej", "czytajwiecej", "czytajdalej",
    "stronagłówna", "stronaglowna", "zalogujsię", "zalogujsie",
    "podzielsię", "podzielsie", "pozdrawiam",
}


def _classify(line: str) -> str | None:
    n = _norm(line)
    if not n:
        return None
    if n in HARD:
        return "hard"
    # widget Blogger/CMS "Subskrybuj[:] komentarze|kanał|posty|(Atom)" — PO "subskrybuj" (i opcjonalnym
    # dwukropku) MUSI iść obiekt-widgetu; sam label ("Subskrybuj:") też OK. Linia krótka (nie akapit).
    # FP-safe: proza "Subskrybuję tę gazetę ... komentarze" i "Subskrybuj: W markecie <opis>" NIE łapane.
    if n.startswith("subskrybuj") and len(n) < 130:
        rest = n[len("subskrybuj"):]
        if rest[:1] == ":":
            rest = rest[1:]
        if (not rest) or rest.startswith(("komentarz", "kanał", "kanal", "posty", "(atom")):
            return "hard"
    if n in SOFT:
        return "soft"
    return None


@check("boilerplate")
def run(ctx) -> list:
    docs = 0
    docs_hard = docs_soft = 0
    hard_lines = soft_lines = 0
    tx = 0
    hard_by_marker: dict[str, int] = {}
    out = []
    for rec in ctx.records:
        ts = texts(rec, ctx.formatka)
        tx += len(ts)
        if not ts:
            continue
        docs += 1
        has_hard = has_soft = False
        for t in ts:
            for line in t.splitlines():
                cls = _classify(line)
                if cls == "hard":
                    hard_lines += 1
                    has_hard = True
                    hard_by_marker[_norm(line)] = hard_by_marker.get(_norm(line), 0) + 1
                elif cls == "soft":
                    soft_lines += 1
                    has_soft = True
        if has_hard:
            docs_hard += 1
        if has_soft:
            docs_soft += 1
    if ctx.records and tx == 0:
        out.append(Issue("error", "boilerplate", "data",
                         "text_fields nie wyłuskało tekstu — skan boilerplate NIE wykonany (blokada; napraw formatkę)"))
        return out
    pct = (100.0 * docs_hard / docs) if docs else 0.0
    if docs_hard:
        top = sorted(hard_by_marker.items(), key=lambda kv: -kv[1])[:5]
        top_s = ", ".join(f"{k}:{v}" for k, v in top)
        out.append(Issue("warn", "boilerplate", "data",
                         f"web-boilerplate HARD: {docs_hard} dok ({pct:.2f}%), {hard_lines} linii — strip przed treningiem [{top_s}]"))
    if soft_lines:
        out.append(Issue("info", "boilerplate", "data",
                         f"boilerplate SOFT (flag-only, FP-podatne, NIE auto-strip): {docs_soft} dok, {soft_lines} linii"))
    if docs and not docs_hard:
        out.append(Issue("info", "boilerplate", "data", "web-boilerplate HARD czyste (0 dok)"))
    return out
