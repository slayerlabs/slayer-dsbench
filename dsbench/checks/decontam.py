"""Dekontaminacja: nakładki pola tekstowego z eval-setami (po HASHACH, nie surowych danych)."""
from __future__ import annotations
import hashlib
import pathlib
from ..models import Issue
from ..registry import check


def _norm(t: str) -> str:
    return " ".join(t.lower().split())


def _find_hashes(start: pathlib.Path):
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
    tf = ctx.formatka.get("text_field", "text")
    over = 0
    for rec in ctx.records:
        t = rec.get(tf)
        if isinstance(t, str):
            if hashlib.sha256(_norm(t).encode("utf-8")).hexdigest() in evalset:
                over += 1
    if over:
        return [Issue("error", "decontam", "data", f"nakładki z eval-setami: {over}")]
    return [Issue("info", "decontam", "data", f"nakładki z eval-setami: 0 ({len(evalset)} hashy)")]
