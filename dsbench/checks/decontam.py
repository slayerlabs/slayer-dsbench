"""Dekontaminacja: nakładki tekstu (nested-aware) z eval-setami (po HASHACH).
FAIL-LOUD: gdy nic nie wyłuskano, OSTRZEGA (nie raportuje „0 nakładek" w próżni)."""
from __future__ import annotations
import hashlib
import pathlib
from ..models import Issue
from ..registry import check
from ..textextract import texts


def _norm(t: str) -> str:
    return " ".join(t.lower().split())


def _find_hashes(start):
    p = pathlib.Path(start).resolve()
    for base in [p, *p.parents][:6]:
        cand = base / "eval_sets" / "hashes.txt"
        if cand.exists():
            return cand
    return None


@check("decontam")
def run(ctx) -> list:
    hp = _find_hashes(ctx.root)
    if not hp:
        return [Issue("info", "decontam", "data", "brak eval_sets/hashes.txt — pominięto")]
    evalset = {ln.strip() for ln in open(hp, encoding="utf-8") if ln.strip() and not ln.startswith("#")}
    over = 0
    tx = 0
    for rec in ctx.records:
        for t in texts(rec, ctx.formatka):
            tx += 1
            if hashlib.sha256(_norm(t).encode("utf-8")).hexdigest() in evalset:
                over += 1
    if ctx.records and tx == 0:
        return [Issue("error", "decontam", "data", "text_fields nie wyłuskało tekstu — dekontaminacja NIE wykonana (blokada; napraw formatkę)")]
    if over:
        return [Issue("error", "decontam", "data", f"nakładki z eval-setami: {over}")]
    return [Issue("info", "decontam", "data", f"nakładki z eval-setami: 0 ({len(evalset)} hashy)")]
