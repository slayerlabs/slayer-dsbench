#!/usr/bin/env python3
"""Tagowanie rejestrow web na GPU (e5 + logreg numpy) + garbage-clean (kill/strip).
Per-slice checkpoint: web-slice-{i}.tagged.parquet; pomija juz zrobione (restart-safe).
Memory-bounded: iter_batches, embed batchami, ParquetWriter w finally.
Slice'y 0-7 (8 packow); 8-9 rezerwa (nietagowane)."""
import sys, os, json, re, time, numpy as np
import pyarrow as pa, pyarrow.parquet as pq
sys.path.insert(0, "/mnt/c/Projekty/Slayer/slayer-dsbench/pipeline")
from garbage_rules import detect
import e5_gpu

WEB = "/mnt/c/Projekty/datasets/build/web"
ES = "/mnt/c/Projekty/Slayer/slayer-dsbench/eval_sets"
Z = np.load(f"{ES}/logreg_coef.npz", allow_pickle=True)
COEF, INTER, CLASSES = Z["coef"], Z["intercept"], Z["classes"].astype(str)

STRIP_RX = [
    re.compile(r"Odwiedziło nas:\s*[\d\s]+osób", re.I),
    re.compile(r"Użytkownicy przeglądający to forum[^.]*\.?", re.I),
    re.compile(r"czytaj\s+więcej|czytaj\s+dalej", re.I),
]
def strip_boiler(t):
    for rx in STRIP_RX:
        t = rx.sub(" ", t)
    return re.sub(r"[ \t]{2,}", " ", t).strip()

def predict(X):
    s = X @ COEF.T + INTER
    return CLASSES[s.argmax(1)]

SCHEMA = pa.schema([("document_id", pa.string()), ("source_id", pa.string()),
    ("text", pa.string()), ("register", pa.string()), ("garbage", pa.bool_()),
    ("license", pa.string()), ("provenance", pa.string())])

def tag_slice(i, bs=2000):
    src = f"{WEB}/web-slice-{i}.parquet"
    out = f"{WEB}/web-slice-{i}.tagged.parquet"
    if os.path.exists(out):
        print(f"[slice {i}] SKIP (checkpoint)"); return
    tmp = out + ".tmp"
    pf = pq.ParquetFile(src)
    kept = dropped = stripped = 0; t0 = time.time()
    w = pq.ParquetWriter(tmp, SCHEMA, compression="zstd")
    try:
        for batch in pf.iter_batches(batch_size=bs, columns=["document_id", "source_id", "text", "license", "provenance"]):
            d = batch.to_pydict()
            texts, keep = [], []
            for j, t in enumerate(d["text"]):
                q, s = detect(t)
                if q:
                    dropped += 1; continue
                tt = strip_boiler(t) if s else (t or "")
                if s: stripped += 1
                texts.append(tt); keep.append(j)
            if not texts:
                continue
            reg = predict(e5_gpu.embed(texts, bs=512, maxlen=160))
            rows = {"document_id": [d["document_id"][k] for k in keep],
                    "source_id": [d["source_id"][k] for k in keep],
                    "text": texts, "register": list(reg),
                    "garbage": [False] * len(keep),
                    "license": [d["license"][k] for k in keep],
                    "provenance": [d["provenance"][k] for k in keep]}
            w.write_table(pa.table(rows, schema=SCHEMA))
            kept += len(keep)
            if kept % 100000 < bs:
                print(f"[slice {i}] kept={kept} drop={dropped} strip={stripped} {kept/(time.time()-t0):.0f} doc/s", flush=True)
    finally:
        w.close()
    os.replace(tmp, out)
    prog = f"{WEB}/tag-progress.json"
    p = json.load(open(prog)) if os.path.exists(prog) else {}
    p[str(i)] = {"kept": kept, "dropped": dropped, "stripped": stripped,
                 "sec": round(time.time() - t0, 1)}
    json.dump(p, open(prog, "w"), indent=2)
    print(f"[slice {i}] DONE kept={kept} drop={dropped} strip={stripped} {round(time.time()-t0)}s", flush=True)

if __name__ == "__main__":
    print("TAG-WEB start", flush=True)
    e5_gpu.load()
    print("e5 loaded", flush=True)
    for i in range(8):
        tag_slice(i)
    print("TAG-WEB ALL DONE", flush=True)
