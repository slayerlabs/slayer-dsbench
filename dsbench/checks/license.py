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
from ..schema import load_yaml

OPEN = ("CC0", "CC-BY", "CC-PD", "PDDL", "ODC-BY", "ODBL", "MIT", "APACHE",
        "PUBLICDOMAIN", "PUBLIC-DOMAIN", "PUBLIC DOMAIN")
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


def _load_manifest(ctx):
    """(mapa {source: license_str}, issues). Pusta mapa gdy karta nie deklaruje source_manifest.
    Akceptuje {sources: {src: {license: SPDX, ...}}} albo płaskie {src: SPDX}."""
    name = ctx.card.get("source_manifest")
    if not name:
        return {}, []
    path = ctx.root / str(name)
    if not path.exists():
        return {}, [Issue("error", "license", "data", f"source_manifest wskazany, brak pliku: {name}")]
    try:
        raw = load_yaml(path) or {}
    except Exception as e:
        return {}, [Issue("error", "license", "data", f"source_manifest nieczytelny ({name}): {e}")]
    src_map = raw.get("sources", raw) if isinstance(raw, dict) else {}
    out = {}
    for s, v in (src_map or {}).items():
        lic = str((v.get("license") if isinstance(v, dict) else v) or "").strip()
        if lic:
            out[str(s)] = lic
    return out, []


def _per_record(ctx, vis) -> list:
    lf = ctx.formatka.get("license_field")
    sf = ctx.formatka.get("source_field")
    manifest, out = _load_manifest(ctx)            # out startuje z ewentualnym błędem manifestu
    if not lf and not manifest:
        return out                                 # brak per-rekord i brak manifestu → parasol karty
    per_source: dict = defaultdict(Counter)        # źródło -> {licencja: liczba}
    covered = 0
    for rec in ctx.records:
        if not isinstance(rec, dict):
            continue
        rec_lic = rec.get(lf) if lf else None
        rec_lic = rec_lic.strip() if isinstance(rec_lic, str) and rec_lic.strip() else None
        src = rec.get(sf) if sf else None
        src = src.strip() if isinstance(src, str) and src.strip() else "(brak źródła)"
        eff = rec_lic or manifest.get(src)         # licencja rekordu WYGRYWA, manifest uzupełnia
        if not eff:
            continue                               # brak jednej i drugiej → parasol karty
        covered += 1
        per_source[src][eff] += 1
    if covered == 0:
        return out                                 # nikt nie niesie licencji → parasol karty
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
