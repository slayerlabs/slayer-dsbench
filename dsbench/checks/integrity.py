"""Integralność (S2): sha256 walidowanego pliku vs karta. Podmiana danych → błąd."""
from __future__ import annotations
import hashlib
from ..models import Issue
from ..registry import check


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


@check("integrity")
def run(ctx) -> list:
    want = ctx.card.get("sha256")
    if not want:
        return [Issue("info", "integrity", "card", "brak sha256 w karcie — pominięto")]
    if not ctx.data_path:
        return [Issue("warn", "integrity", "data", "sha256 w karcie, ale brak pliku danych do sprawdzenia")]
    got = sha256_file(ctx.data_path)
    if got.lower() != str(want).lower():
        return [Issue("error", "integrity", "data",
                      f"sha256 NIEZGODNE: karta={str(want)[:12]}… plik={got[:12]}… (podmiana danych?)")]
    return [Issue("info", "integrity", "data", "sha256 OK")]
