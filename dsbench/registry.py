"""Rejestr checków (open/closed): nowy check = nowy plik + @check(id), zero zmian w silniku."""
from __future__ import annotations

_REG: dict = {}


def check(cid: str):
    def deco(fn):
        if cid in _REG:
            raise ValueError(f"check '{cid}' już zarejestrowany")
        _REG[cid] = fn
        return fn
    return deco


def get(cid: str):
    if cid not in _REG:
        raise KeyError(f"nieznany check '{cid}' (dostępne: {', '.join(names())})")
    return _REG[cid]


def names() -> list:
    return sorted(_REG)
