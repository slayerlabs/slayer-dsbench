"""Licencja DWUPOZIOMOWA (dynaword) + wewn./zewn.: external MUSI mieć otwartą licencję tekstu;
kolekcja/metadane domyślnie CC0."""
from __future__ import annotations
from ..models import Issue
from ..registry import check

OPEN = ("CC0", "CC-BY", "CC-PD", "PDDL", "ODC-BY", "ODBL", "MIT", "APACHE", "PUBLICDOMAIN")


def _is_open(lic: str) -> bool:
    return any(lic.upper().startswith(o) for o in OPEN)


@check("license")
def run(ctx) -> list:
    out = []
    lic = str(ctx.card.get("license") or "").strip()   # licencja TEKSTU/danych (źródło)
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
    return out
