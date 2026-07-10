"""Licencja DWUPOZIOMOWA (dynaword) + wewn./zewn.

Dwa poziomy granulacji, jeden check:
  • KARTA  — deklaracja parasolowa: jedna `license` (tekst) + `collection_license` (metadane).
  • REKORD — licencja PER DOKUMENT/ŹRÓDŁO (opcjonalna, sterowana formatką: `license_field`,
             `source_field`). Realny blob (speakleash/dynaword) to KOMPILACJA wielu źródeł
             o RÓŻNYCH licencjach — pojedyncze pole na karcie tego nie wyraża. Skrypt źródłowy
             przypisuje licencję per źródło; bramka to konsumuje: pod `external` KAŻDY dokument
             musi być otwarty, inaczej kompilacja jest zatruta licencyjnie (jeden NC/ND/zamknięty
             dokument = ❌).

Zero hardkodu pól: nazwy pól rekordu czytane z formatki (jak `text_fields`/`id_field`).
Gdy formatka nie wskazuje `license_field` albo rekordy go nie niosą → obowiązuje parasol karty
(pełna wsteczna zgodność — dawne datasety bez zmian)."""
from __future__ import annotations
from collections import Counter, defaultdict
from ..models import Issue
from ..registry import check

OPEN = ("CC0", "CC-BY", "CC-PD", "PDDL", "ODC-BY", "ODBL", "MIT", "APACHE", "PUBLICDOMAIN")
RESTRICTED = ("-NC", "-ND")   # non-commercial / no-derivatives → NIE do wolnej redystrybucji


def _status(lic: str) -> str:
    """'open' | 'restricted' | 'unknown' po normalizacji SPDX-ish.
    NC/ND (np. CC-BY-NC-4.0) NIE są otwarte, mimo prefiksu CC-BY."""
    u = lic.upper().strip()
    if not u:
        return "unknown"
    if any(tok in u for tok in RESTRICTED):
        return "restricted"
    if any(u.startswith(o) for o in OPEN):
        return "open"
    return "unknown"


def _is_open(lic: str) -> bool:
    return _status(lic) == "open"


@check("license")
def run(ctx) -> list:
    out = []
    lic = str(ctx.card.get("license") or "").strip()   # licencja TEKSTU/danych (parasol źródła)
    vis = ctx.card.get("visibility")
    if vis == "external":
        if not lic:
            out.append(Issue("error", "license", "card", "external BEZ licencji tekstu — wymagana otwarta licencja"))
        elif not _is_open(lic):
            out.append(Issue("warn", "license", "card", f"licencja tekstu '{lic}' nie wygląda na otwartą (SPDX) — sprawdź"))
        else:
            out.append(Issue("info", "license", "card", f"licencja tekstu: {lic}"))
    elif vis == "internal":
        if not lic:
            out.append(Issue("warn", "license", "card", "internal bez licencji (OK, ale oznacz prawa/źródło)"))
        else:
            out.append(Issue("info", "license", "card", f"internal, licencja tekstu: {lic}"))
    coll = str(ctx.card.get("collection_license") or "CC0-1.0").strip()   # kolekcja/metadane (dynaword)
    out.append(Issue("info", "license", "card", f"licencja kolekcji/metadanych: {coll}"))

    # PER DOKUMENT/ŹRÓDŁO — aktywne tylko gdy formatka wskazuje pole i rekordy je niosą.
    out += _per_record(ctx, vis)
    return out


def _per_record(ctx, vis) -> list:
    lf = ctx.formatka.get("license_field")
    if not lf:
        return []                                  # formatka nie deklaruje licencji per-rekord
    sf = ctx.formatka.get("source_field")
    per_source: dict = defaultdict(Counter)        # źródło -> {licencja: liczba}
    covered = 0
    for rec in ctx.records:
        if not isinstance(rec, dict):
            continue
        val = rec.get(lf)
        if not isinstance(val, str) or not val.strip():
            continue                               # rekord bez licencji → obowiązuje parasol karty
        covered += 1
        src = rec.get(sf) if sf else None
        src = src.strip() if isinstance(src, str) and src.strip() else "(brak źródła)"
        per_source[src][val.strip()] += 1
    if covered == 0:
        return []                                  # nikt nie niesie licencji → parasol karty

    out = []
    summary = "; ".join(
        f"{src}: " + ", ".join(f"{l}×{n}" for l, n in sorted(cnt.items()))
        for src, cnt in sorted(per_source.items())
    )
    out.append(Issue("info", "license", "data", f"licencje per źródło ({covered} dok.): {summary}"))

    restricted: dict = defaultdict(int)
    unknown: dict = defaultdict(int)
    for cnt in per_source.values():
        for l, n in cnt.items():
            st = _status(l)
            if st == "restricted":
                restricted[l] += n
            elif st == "unknown":
                unknown[l] += n

    if vis == "external":
        if restricted:
            det = ", ".join(f"{l}×{n}" for l, n in sorted(restricted.items()))
            out.append(Issue("error", "license", "data",
                             f"external: dokumenty z licencją NIE-otwartą (NC/ND/zamknięta): {det} "
                             "— usuń lub przeklasyfikuj (zatruwają kompilację)"))
        if unknown:
            det = ", ".join(f"{l}×{n}" for l, n in sorted(unknown.items()))
            out.append(Issue("warn", "license", "data",
                             f"external: licencje per-dok nierozpoznane (nie-SPDX?): {det} — zweryfikuj"))
    return out
