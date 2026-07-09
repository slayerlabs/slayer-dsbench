"""Licencja + wewn./zewn.: external MUSI mieć otwartą licencję; internal — ostrzeżenie gdy brak."""
from __future__ import annotations
from ..models import Issue
from ..registry import check

OPEN = ("CC0", "CC-BY", "CC-PD", "PDDL", "ODC-BY", "ODBL", "MIT", "APACHE", "PUBLICDOMAIN")


@check("license")
def run(ctx) -> list:
    out = []
    lic = str(ctx.card.get("license") or "").strip()
    vis = ctx.card.get("visibility")
    if vis == "external":
        if not lic:
            out.append(Issue("error", "license", "card", "dataset external BEZ licencji — wymagana otwarta licencja"))
        elif not any(lic.upper().startswith(o) for o in OPEN):
            out.append(Issue("warn", "license", "card", f"licencja '{lic}' nie wygląda na otwartą (SPDX) — sprawdź"))
        else:
            out.append(Issue("info", "license", "card", f"licencja: {lic}"))
    elif vis == "internal":
        if not lic:
            out.append(Issue("warn", "license", "card", "internal bez licencji (OK, ale oznacz źródło/prawa)"))
        else:
            out.append(Issue("info", "license", "card", f"internal, licencja: {lic}"))
    return out
