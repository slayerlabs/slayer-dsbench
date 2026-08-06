"""Near-duplicate treści (fuzzy): MinHash + LSH-banding, uzupełnia exact `dedup` (sha1).
Łapie prawie-identyczne dokumenty (boilerplate, re-scrape, drobne różnice) których hash exact gubi.
WARN (nie ERROR): near-dup bywa legalny (podobne-ale-różne) — sygnał do przeglądu, nie twardy blok.

Czysto-python (hashlib blake2b + trik (a·h+b) mod p), zero zależności ponad stdlib.
Skanuje wyłuskany tekst (nested-aware). Na pełnych blobach podawaj sample/shard (jak reszta dsbench)."""
from __future__ import annotations
import hashlib
from ..models import Issue
from ..registry import check
from ..textextract import texts

_K = 5          # k-słowowe shingle
_N = 64         # permutacje MinHash
_BANDS = 16     # LSH: 16 pasm × 4 wiersze (próg ~ (1/b)^(1/r) ≈ 0.5, weryfikacja jaccardem)
_ROWS = _N // _BANDS
_THR = 0.8      # próg near-dup (estymata jaccarda z pełnego podpisu)
_P = (1 << 61) - 1
# deterministyczne (a,b) dla _N funkcji haszujących (seed stały → reprodukowalnie)
_AB = [(pow(7, i + 1, _P) | 1, pow(13, i + 1, _P)) for i in range(_N)]


def _shingles(text: str) -> set:
    w = text.split()
    if len(w) < _K:
        return {text.strip()} if text.strip() else set()
    return {" ".join(w[i:i + _K]) for i in range(len(w) - _K + 1)}


def _sig(sh: set) -> tuple:
    if not sh:
        return tuple([0] * _N)
    base = [int.from_bytes(hashlib.blake2b(s.encode("utf-8"), digest_size=8).digest(), "big") for s in sh]
    return tuple(min((a * h + b) % _P for h in base) for a, b in _AB)


def _est_jaccard(s1: tuple, s2: tuple) -> float:
    return sum(1 for a, b in zip(s1, s2) if a == b) / _N


@check("neardup")
def run(ctx) -> list:
    sigs = []
    for rec in ctx.records:
        ts = texts(rec, ctx.formatka)
        blob = "\n".join(ts) if ts else ""
        sigs.append(_sig(_shingles(blob)))
    # LSH: kubełkuj po pasmach → kandydaci; weryfikuj pełnym podpisem
    near = 0
    dup_of = [-1] * len(sigs)
    buckets: dict = {}
    for i, sig in enumerate(sigs):
        cand = set()
        for band in range(_BANDS):
            key = (band, sig[band * _ROWS:(band + 1) * _ROWS])
            cand.update(buckets.get(key, ()))
            buckets.setdefault(key, []).append(i)
        for j in cand:
            if dup_of[i] == -1 and _est_jaccard(sig, sigs[j]) >= _THR:
                dup_of[i] = j
                near += 1
                break
    if near:
        return [Issue("warn", "neardup", "data",
                      f"near-duplikaty (fuzzy, jaccard≥{_THR}): {near} — rozważ dedup (exact hash ich nie łapie)")]
    return [Issue("info", "neardup", "data", "near-duplikaty: 0")]
