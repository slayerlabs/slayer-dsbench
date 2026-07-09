"""Ekstrakcja tekstu z rekordu — pola PŁASKIE i ZAGNIEŻDŻONE (np. messages[].content).
Sterowane formatką (`text_fields` lista, fallback `text_field`). Wspólne dla checków tekstowych.
Dzięki temu checki nie dają FAŁSZYWEGO ZIELONEGO na formatach chat/nested."""
from __future__ import annotations


def _specs(fmt: dict) -> list:
    tf = fmt.get("text_fields")
    if tf:
        return list(tf)
    single = fmt.get("text_field")
    return [single] if single else ["text"]


def texts(rec: dict, fmt: dict) -> list:
    """Zwraca listę stringów tekstu z rekordu. `messages[].content` → treść każdego elementu listy."""
    out = []
    for spec in _specs(fmt):
        if "[]." in spec:
            base, sub = spec.split("[].", 1)
            arr = rec.get(base)
            if isinstance(arr, list):
                for it in arr:
                    if isinstance(it, dict) and isinstance(it.get(sub), str):
                        out.append(it[sub])
        else:
            v = rec.get(spec)
            if isinstance(v, str):
                out.append(v)
    return out


def text_bases(fmt: dict) -> set:
    """Nazwy pól-baz tekstu (do wykluczenia z osobnego skanu metadanych)."""
    return {spec.split("[].", 1)[0] if "[]." in spec else spec for spec in _specs(fmt)}
