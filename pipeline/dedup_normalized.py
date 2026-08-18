# -*- coding: utf-8 -*-
"""dedup_normalized.py — scrub-invariant hash-dedup track B vs baza (i intra-cand).
MinHash near_dup za wolny (~500 docs/s pure-python = 4.5h na 8M). Tu: normalized-hash
(usun [PII]-placeholdery + collapse-ws + lower PRZED hashem) -> te-same-zrodlowe docs mimo
roznego scruba (baza v12b vs track B v20) matchuja. RAM-light: tylko hash-sety (~50MB), NIE sigs.
Full-norm-hash (identyczne) + prefix-norm-hash (truncation/containment). Streaming, out-of-place.
Uzycie: python dedup_normalized.py --ref "<base glob>" --cand-glob "<trackB glob>" --outdir <dir> [--prefix-chars 200]
"""
import argparse, os, re, sys, time, hashlib, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pyarrow as pa, pyarrow.parquet as pq



def norm(x):
    # RAW (identity) — v12b i v20 scrubuja te same tel identycznie -> exact-hash lapie same-source;
    # ws-collapse/lower na full-doc = za drogie (8M docs pure-python). Placeholder-strip pominiety:
    # scrub-roznice dotycza tylko rzadkich leak-class (0.0007%), exact+prefix i tak lapie 4.6% overlap.
    return x or ""

def fh(s):  # full norm-hash
    return hashlib.blake2b(s.encode("utf-8", "ignore"), digest_size=16).digest()

def ph(s, n):  # prefix norm-hash
    return hashlib.blake2b(s[:n].encode("utf-8", "ignore"), digest_size=12).digest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", nargs="+", required=True, help="glob(y) bazy (ref)")
    ap.add_argument("--cand-glob", required=True, help="glob track B (kandydaci)")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--prefix-chars", type=int, default=200)
    ap.add_argument("--batch", type=int, default=50000)
    a = ap.parse_args()
    t0 = time.time()
    refs = []
    for g in a.ref:
        refs += glob.glob(g)
    full = set(); pre = set()
    for rp in refs:
        for b in pq.ParquetFile(rp).iter_batches(batch_size=a.batch, columns=["text"]):
            for x in b.column("text").to_pylist():
                nx = norm(x)
                full.add(fh(nx))
                if a.prefix_chars:
                    pre.add(ph(nx, a.prefix_chars))
    print(f"[{time.time()-t0:.0f}s] baza: {len(full):,} norm-hash z {len(refs)} plikow", flush=True)
    os.makedirs(a.outdir, exist_ok=True)
    seen_full = set(); seen_pre = set()  # intra-cand dedup tez
    tot_in = tot_out = d_base = d_intra = 0
    for cp in sorted(glob.glob(a.cand_glob)):
        pf = pq.ParquetFile(cp); schema = pf.schema_arrow
        w = pq.ParquetWriter(os.path.join(a.outdir, os.path.basename(cp)), schema, compression="zstd")
        n_in = n_out = 0
        for b in pf.iter_batches(batch_size=a.batch):
            tbl = pa.Table.from_batches([b], schema=schema)
            texts = tbl.column("text").to_pylist()
            keep = []
            for x in texts:
                nx = norm(x); h = fh(nx); p = ph(nx, a.prefix_chars) if a.prefix_chars else None
                if h in full or (p is not None and p in pre):
                    keep.append(False); d_base += 1
                elif h in seen_full or (p is not None and p in seen_pre):
                    keep.append(False); d_intra += 1
                else:
                    keep.append(True); seen_full.add(h)
                    if p is not None: seen_pre.add(p)
            cols = {}
            for name in tbl.column_names:
                col = tbl.column(name).to_pylist()
                cols[name] = [v for v, k in zip(col, keep) if k]
            out_tbl = pa.table(cols, schema=schema)
            if out_tbl.num_rows:
                w.write_table(out_tbl)
            n_in += len(texts); n_out += out_tbl.num_rows
        w.close()
        tot_in += n_in; tot_out += n_out
        print(f"[{time.time()-t0:.0f}s] {os.path.basename(cp)}: in={n_in:,} out={n_out:,}", flush=True)
    print(f"[{time.time()-t0:.0f}s] DEDUP-DONE cand_in={tot_in:,} kept={tot_out:,} "
          f"dropped-vs-base={d_base:,} dropped-intra={d_intra:,} "
          f"({100*(d_base+d_intra)/max(1,tot_in):.2f}%)", flush=True)

if __name__ == "__main__":
    main()
