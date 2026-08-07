# -*- coding: utf-8 -*-
"""near_dup_vs_dynaword.py — cross-source near-dedup: dropuj kandydatów (HPLT-cleaned)
near-duplikatowych względem ISTNIEJĄCEGO korpusu (dynaword). Luka z PR#5 („near_dup left downstream").

Reużywa proven params z labvault near_dup.py (14_07_Frame-Merge): 5-słów shingle, crc32,
MinHash-128, LSH 16×8. KLUCZ cross-source: ref+cand ten sam seed → identyczne permutacje → sigi porównywalne.
Jaccard estymowany z MinHash (mean(sig_a==sig_b)). Deterministyczne.

Użycie:
  python near_dup_vs_dynaword.py --ref "data/wikipedia/*.parquet" --cand hplt.parquet --threshold 0.8
  --limit-ref N (sample ref dla feasibility) · --out kept.parquet (opcjonalnie zapis odsianych)
"""
import re, time, glob, argparse, zlib, hashlib
import numpy as np
import pyarrow as pa, pyarrow.parquet as pq

WORD = re.compile(r"\w+", re.UNICODE)
P = 2**31 - 1
NUM_PERM, BANDS, ROWS = 128, 16, 8  # BANDS*ROWS == NUM_PERM

def shingles(text, k=5):
    w = WORD.findall(text.lower())
    if len(w) < k:
        return {" ".join(w)} if w else set()
    return {" ".join(w[i:i+k]) for i in range(len(w) - k + 1)}

def h31(s):
    return zlib.crc32(s.encode("utf-8")) & 0x7fffffff

def pre(t, n=200):
    """prefix-signature (Latarnik): md5 pierwszych-400-znakow -> norm-whitespace -> first-n -> lower.
    Lapie truncation-variants (base=truncated-prefix cand) ktore Jaccard-MinHash gubi (low-J)."""
    return hashlib.md5(re.sub(r"\s+", " ", (t or "")[:400]).strip().lower()[:n].encode("utf-8", "ignore")).hexdigest()

def _perms(seed=1):
    rng = np.random.default_rng(seed)
    return rng.integers(1, P, NUM_PERM).astype(np.int64), rng.integers(0, P, NUM_PERM).astype(np.int64)

def minhash(texts, a, b, chunk=1024):
    MAX = np.int64(P)
    sig = np.full((len(texts), NUM_PERM), MAX, dtype=np.int64)
    for i, t in enumerate(texts):
        sh = shingles(t)
        if not sh:
            continue
        hs = np.fromiter((h31(s) for s in sh), dtype=np.int64, count=len(sh))
        best = np.full(NUM_PERM, MAX, dtype=np.int64)
        for j in range(0, len(hs), chunk):
            blk = hs[j:j+chunk]
            vals = (a[:, None] * blk[None, :] + b[:, None]) % P
            np.minimum(best, vals.min(axis=1), out=best)
        sig[i] = best
    return sig

def build_index(ref_sig):
    """band -> {band_bytes -> [ref_ids]}"""
    idx = [dict() for _ in range(BANDS)]
    for r in range(ref_sig.shape[0]):
        for band in range(BANDS):
            key = ref_sig[r, band*ROWS:(band+1)*ROWS].tobytes()
            idx[band].setdefault(key, []).append(r)
    return idx

def load_texts(patterns, limit=0):
    texts = []
    for pat in patterns:
        for fp in sorted(glob.glob(pat)):
            t = pq.read_table(fp, columns=["text"])
            texts.extend(t.column("text").to_pylist())
            if limit and len(texts) >= limit:
                return texts[:limit]
    return texts

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", nargs="+", required=True, help="glob(y) parquetów referencyjnych (dynaword)")
    ap.add_argument("--cand", required=True, help="parquet kandydatów (HPLT-cleaned)")
    ap.add_argument("--threshold", type=float, default=0.8, help="Jaccard-MinHash próg near-dup")
    ap.add_argument("--limit-ref", type=int, default=0, help="cap sample referencji (feasibility)")
    ap.add_argument("--limit-cand", type=int, default=0)
    ap.add_argument("--out", default="", help="parquet odsianych kandydatów (opcjonalnie)")
    ap.add_argument("--prefix-chars", type=int, default=0, help="prefix-sig dedup (Latarnik containment/truncation-lens): drop cand gdy prefix-sig w ref; 0=off, 200=zalecane")
    a = ap.parse_args()
    t0 = time.time()
    A, B = _perms(1)

    ref = load_texts(a.ref, a.limit_ref)
    ref_sig = minhash(ref, A, B)
    idx = build_index(ref_sig)
    print(f"[{time.time()-t0:.0f}s] ref docs={len(ref)} zindeksowane", flush=True)
    ref_pre = set(pre(t, a.prefix_chars) for t in ref) if a.prefix_chars else set()

    cand = load_texts([a.cand], a.limit_cand)
    cand_sig = minhash(cand, A, B)
    print(f"[{time.time()-t0:.0f}s] cand docs={len(cand)} sig gotowe", flush=True)

    dropped = 0
    keep_mask = np.ones(len(cand), dtype=bool)
    for c in range(len(cand)):
        seen = set()
        for band in range(BANDS):
            key = cand_sig[c, band*ROWS:(band+1)*ROWS].tobytes()
            for r in idx[band].get(key, ()):
                seen.add(r)
        best = 0.0
        for r in seen:
            jac = float(np.mean(cand_sig[c] == ref_sig[r]))
            if jac > best:
                best = jac
            if best >= a.threshold:
                break
        if best >= a.threshold or (a.prefix_chars and pre(cand[c], a.prefix_chars) in ref_pre):
            keep_mask[c] = False
            dropped += 1
    kept = int(keep_mask.sum())
    rate = 100.0 * dropped / max(1, len(cand))
    print(f"[{time.time()-t0:.0f}s] RESULT cand={len(cand)} dropped_near_dup={dropped} ({rate:.1f}%) kept={kept} thr={a.threshold}", flush=True)

    if a.out and kept:
        tbl = pq.read_table(a.cand)
        tbl = tbl.filter(pa.array(keep_mask.tolist()))
        pq.write_table(tbl, a.out, compression="zstd")
        print(f"[{time.time()-t0:.0f}s] zapis kept -> {a.out} ({kept} docs)", flush=True)

if __name__ == "__main__":
    main()
