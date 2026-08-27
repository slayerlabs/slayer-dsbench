"""Register-tag: WALIDACJA + RAPORT datasetu otagowanego rejestrami (nie klasyfikuje — sprawdza wynik klasyfikatora).
FAIL-LOUD: gdy check włączony a pole register nieobecne = błąd (dataset nie jest register-tagged).
Pola z formatki: `register_field` (dom. 'register'), `garbage_field` (dom. 'garbage')."""
from __future__ import annotations
from collections import Counter
from ..models import Issue
from ..registry import check

KNOWN = {"news", "howto", "qa", "dialog", "literacki", "nauka",
         "encyklopedyczny", "opinie", "legal", "web-inne"}
GATE = {"dialog", "qa", "howto", "nauka", "literacki"}  # bramkowane do mixu jako diverse


@check("register")
def run(ctx) -> list:
    fmt = ctx.formatka or {}
    rfield = fmt.get("register_field", "register")
    gfield = fmt.get("garbage_field", "garbage")
    recs = [r for r in ctx.records if isinstance(r, dict)]
    if not recs:
        return [Issue("info", "register", "data", "brak rekordów")]
    tagged = [r for r in recs if r.get(rfield) not in (None, "")]
    if not tagged:
        return [Issue("error", "register", "data",
                      f"pole '{rfield}' nieobecne — dataset nie jest register-tagged (blokada)")]
    issues = []
    dist = Counter(r.get(rfield) for r in tagged)
    unknown = {k: v for k, v in dist.items() if k not in KNOWN}
    if unknown:
        issues.append(Issue("error", "register", "data",
                            f"rejestry spoza słownika ({len(KNOWN)}): {unknown}"))
    top = ", ".join(f"{k}={v}" for k, v in dist.most_common())
    issues.append(Issue("info", "register", "data", f"rozkład rejestrów ({len(tagged)} rek.): {top}"))
    ng = sum(1 for r in tagged if r.get(gfield) in (True, "true", "True", 1, "1"))
    if ng:
        issues.append(Issue("info", "register", "data", f"garbage-flag: {ng} ({100 * ng / len(tagged):.1f}%)"))
    missing = [g for g in sorted(GATE) if dist.get(g, 0) == 0]
    if missing:
        issues.append(Issue("warn", "register", "data", f"brak rejestrów bramkowanych: {missing}"))
    if len(tagged) < len(recs):
        issues.append(Issue("warn", "register", "data",
                            f"rekordy bez rejestru: {len(recs) - len(tagged)} (nieotagowane)"))
    return issues
