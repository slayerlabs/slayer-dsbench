# -*- coding: utf-8 -*-
"""drop_docs.py — usun docs po doc-id (kolumna 'id') z listy Wartownika (A-prim drop-gate).
STREAMING (iter_batches), out-of-place (--outdir, zero os.replace = brak Windows-AV-lock).
Drop-lista = plik z jednym doc-id na linie (kolumna 'id' parquetu). Terminal-krok po b2:
kazdy flagowany doc (real+FP, mechanicznie) -> drop -> final b2 = leak/idem/mangle=0 -> GREEN.
Uzycie: python drop_docs.py --parquet <path> --dropids <file> --outdir <dir>
"""
import argparse, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pyarrow as pa, pyarrow.parquet as pq

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", required=True)
    ap.add_argument("--dropids", required=True, help="plik: jeden doc-id (kolumna 'id') na linie")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--batch", type=int, default=20000)
    a = ap.parse_args()
    t0 = time.time()
    with open(a.dropids, encoding="utf-8") as f:
        drop = {ln.strip() for ln in f if ln.strip()}
    pf = pq.ParquetFile(a.parquet)
    schema = pf.schema_arrow
    if "id" not in schema.names:
        print(f"ERR {os.path.basename(a.parquet)}: brak kolumny 'id'", flush=True); sys.exit(2)
    out_path = os.path.join(a.outdir, os.path.basename(a.parquet))
    writer = pq.ParquetWriter(out_path, schema, compression="zstd")
    n_in = n_out = dropped = 0
    for batch in pf.iter_batches(batch_size=a.batch):
        tbl = pa.Table.from_batches([batch], schema=schema)
        ids = tbl.column("id").to_pylist()
        n_in += len(ids)
        keep = [str(i) not in drop for i in ids]
        d = keep.count(False); dropped += d
        if all(keep):
            out_tbl = tbl
        else:
            cols = {name: [v for v, k in zip(tbl.column(name).to_pylist(), keep) if k] for name in tbl.column_names}
            out_tbl = pa.table(cols, schema=schema)
        if out_tbl.num_rows:
            writer.write_table(out_tbl)
        n_out += out_tbl.num_rows
    writer.close()
    print(f"{os.path.basename(a.parquet)}: in={n_in:,} out={n_out:,} dropped={dropped} ({time.time()-t0:.0f}s)", flush=True)

if __name__ == "__main__":
    main()
