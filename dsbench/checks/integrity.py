"""Integralność (S2): sha256 pliku vs karta + zgodność liczby rekordów (num_examples, styl HF).
num_examples liczony TYLKO na pełnych danych, nie na próbce."""
from __future__ import annotations
import hashlib
import os
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
    out = []
    want = ctx.card.get("sha256")
    if not want:
        out.append(Issue("info", "integrity", "card", "brak sha256 w karcie — pominięto"))
    elif not ctx.data_path:
        out.append(Issue("warn", "integrity", "data", "sha256 w karcie, ale brak pliku danych"))
    else:
        got = sha256_file(ctx.data_path)
        if got.lower() != str(want).lower():
            out.append(Issue("error", "integrity", "data",
                             f"sha256 NIEZGODNE: karta={str(want)[:12]}… plik={got[:12]}… (podmiana danych?)"))
        else:
            out.append(Issue("info", "integrity", "data", "sha256 OK"))

    want_n = ctx.card.get("records")   # num_examples (HF-style)
    if want_n is not None and ctx.data_path:
        is_sample = os.path.basename(ctx.data_path) == str(ctx.card.get("sample", ""))
        if is_sample:
            out.append(Issue("info", "integrity", "data", f"records={want_n} (deklaracja; walidacja na próbce — totalu nie liczę)"))
        elif len(ctx.records) != want_n:
            out.append(Issue("error", "integrity", "data", f"liczba rekordów {len(ctx.records)} ≠ records={want_n} (karta)"))
        else:
            out.append(Issue("info", "integrity", "data", f"liczba rekordów zgodna: {want_n}"))
    return out
