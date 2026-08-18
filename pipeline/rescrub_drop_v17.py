# -*- coding: utf-8 -*-
"""rescrub_drop_v17.py — v17 re-scrub in-place + DROP docs z mangle. STREAMING (row-group).
FCD-R7 lekcja ZASTOSOWANA: iter_batches + ParquetWriter -> RAM staly ~batch (NIE read_table calego
pliku = 8GB Arrow/worker). v17 domyka foreign-14/dual-slash (LEAKI, numery obecne -> re-scrub lapie);
mangle (cyfry zjedzone) -> DROP (re-scrub nie przywroci). Temp+rename (atomowy).
Uzycie: python rescrub_drop_v17.py --parquet <path> [--max-pii-frac 0.02] [--batch 20000]
"""
import argparse, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pyarrow as pa, pyarrow.parquet as pq
import clean_hplt_v3 as C

MANGLE = re.compile(r"\[Telefon\][-\d]|\d\[Telefon\]")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", required=True)
    ap.add_argument("--max-pii-frac", type=float, default=0.02)
    ap.add_argument("--batch", type=int, default=20000)
    a = ap.parse_args()
    t0 = time.time()
    pf = pq.ParquetFile(a.parquet)
    schema = pf.schema_arrow
    tmp = a.parquet + ".v17tmp"
    writer = pq.ParquetWriter(tmp, schema, compression="zstd")
    n_in = n_out = changed = dropped = 0
    resid_e = resid_p = resid_n = 0
    for batch in pf.iter_batches(batch_size=a.batch):
        tbl = pa.Table.from_batches([batch], schema=schema)
        texts = tbl.column("text").to_pylist()
        n_in += len(texts)
        new_text = []; keep = []
        for x in texts:
            out, _, _ = C.scrub_pii(x or "", None, a.max_pii_frac)
            if MANGLE.search(out):
                keep.append(False); dropped += 1
                continue
            keep.append(True)
            if out != (x or ""):
                changed += 1
            new_text.append(out)
            resid_e += len(C.EMAIL_RE.findall(out)); resid_p += len(C.PHONE_RE.findall(out)); resid_n += len(C.NATID_RE.findall(out))
        cols = {}
        for name in tbl.column_names:
            if name == "text":
                cols[name] = new_text
            else:
                col = tbl.column(name).to_pylist()
                cols[name] = [v for v, k in zip(col, keep) if k]
        out_tbl = pa.table(cols, schema=schema)
        if out_tbl.num_rows:
            writer.write_table(out_tbl)
        n_out += len(new_text)
    writer.close()
    os.replace(tmp, a.parquet)
    print(f"{os.path.basename(a.parquet)}: in={n_in:,} out={n_out:,} "
          f"v17-changed={changed:,} dropped-mangle={dropped} "
          f"resid(e/p/n)={resid_e}/{resid_p}/{resid_n} ({time.time()-t0:.0f}s)", flush=True)

if __name__ == "__main__":
    main()
