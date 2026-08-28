#!/usr/bin/env python3
"""Assembly slayer-pl-8x3b. Shared backbone (core/core_sa/legal/legal_sa/en) + pack-XX/web.parquet
(cap ~1.89B wg sum przebiegu web), manifesty (sha256 + tokeny + rozklad rejestrow + SA), sample.jsonl,
aktualizacja dataset.json. Idempotentne: pomija istniejace pliki wyjsciowe (restart-safe)."""
import glob, os, json, hashlib, time
import pyarrow as pa, pyarrow.parquet as pq

DS = "/mnt/c/Projekty/datasets/slayer-pl-8x3b"
BUILD = "/mnt/c/Projekty/datasets/build"
WEB = f"{BUILD}/web"
SHARED = f"{DS}/shared"
os.makedirs(SHARED, exist_ok=True)

SCHEMA = pa.schema([("document_id", pa.string()), ("source_id", pa.string()), ("text", pa.string()),
    ("register", pa.string()), ("license", pa.string()), ("provenance", pa.string()),
    ("classified_by", pa.string()), ("garbage", pa.bool_())])

WS = json.load(open(f"{BUILD}/web-backbone-stats.json"))
SLICE_TOK, SLICE_DOCS = WS["slice_tok"], WS["slice_docs"]
CORE_TOK = json.load(open(f"{BUILD}/shared-core-FINAL.json"))["total_tokens_cl100k"]

def sha256(path, buf=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(buf), b""):
            h.update(b)
    return h.hexdigest()

def norm(d, classified_by):
    n = len(d["text"])
    g = d.get("garbage") or [False] * n
    return {"document_id": d.get("document_id") or [None] * n, "source_id": d.get("source_id") or [None] * n,
            "text": d["text"], "register": d.get("register") or [None] * n,
            "license": d.get("license") or [None] * n, "provenance": d.get("provenance") or [None] * n,
            "classified_by": [classified_by] * n, "garbage": g}

def stream(src_files, out, classified_by, sa_route=False, sa_out=None, bs=4000):
    """Stream src parquet(s) -> out (schema 8-col). Jesli sa_route: wiersze is_share_alike=True -> sa_out.
    Zwraca (rows, sa_rows, text_bytes, sa_text_bytes)."""
    if os.path.exists(out) and (not sa_route or os.path.exists(sa_out)):
        pf = pq.ParquetFile(out); r = pf.metadata.num_rows
        sr = pq.ParquetFile(sa_out).metadata.num_rows if sa_route else 0
        print(f"  SKIP {os.path.basename(out)} (checkpoint) rows={r} sa={sr}")
        return r, sr, None, None
    w = pq.ParquetWriter(out, SCHEMA, compression="zstd")
    wsa = pq.ParquetWriter(sa_out, SCHEMA, compression="zstd") if sa_route else None
    rows = sa_rows = tb = satb = 0
    try:
        for f in src_files:
            pf = pq.ParquetFile(f)
            has_sa = "is_share_alike" in pf.schema_arrow.names
            cols = None
            for batch in pf.iter_batches(batch_size=bs):
                d = batch.to_pydict()
                if sa_route and has_sa:
                    sa_flag = d["is_share_alike"]
                    perm = {k: [v for v, s in zip(d[k], sa_flag) if not s] for k in d}
                    sar = {k: [v for v, s in zip(d[k], sa_flag) if s] for k in d}
                    if perm["text"]:
                        t = norm(perm, classified_by); w.write_table(pa.table(t, schema=SCHEMA))
                        rows += len(t["text"]); tb += sum(len(x or "") for x in t["text"])
                    if sar["text"]:
                        t = norm(sar, classified_by); wsa.write_table(pa.table(t, schema=SCHEMA))
                        sa_rows += len(t["text"]); satb += sum(len(x or "") for x in t["text"])
                else:
                    t = norm(d, classified_by); w.write_table(pa.table(t, schema=SCHEMA))
                    rows += len(t["text"]); tb += sum(len(x or "") for x in t["text"])
    finally:
        w.close()
        if wsa: wsa.close()
    print(f"  {os.path.basename(out)} rows={rows} sa={sa_rows}")
    return rows, sa_rows, tb, satb

def pack_web(i, bs=4000):
    src = f"{WEB}/web-slice-{i}.tagged.parquet"
    pd = f"{DS}/pack-{i:02d}"; os.makedirs(pd, exist_ok=True)
    out = f"{pd}/web.parquet"
    M = round(1.89e9 * SLICE_DOCS[i] / SLICE_TOK[i])  # tyle wierszy ~= 1.89B tok
    if os.path.exists(out):
        print(f"  SKIP pack-{i:02d}/web.parquet (checkpoint)")
        return out, M
    w = pq.ParquetWriter(out, SCHEMA, compression="zstd"); got = 0
    from collections import Counter
    reg = Counter()
    try:
        for batch in pq.ParquetFile(src).iter_batches(batch_size=bs):
            if got >= M: break
            d = batch.to_pydict(); take = min(bs, M - got)
            d = {k: v[:take] for k, v in d.items()}
            t = norm(d, "multilingual-e5+logreg"); w.write_table(pa.table(t, schema=SCHEMA))
            got += len(t["text"]); reg.update(t["register"])
    finally:
        w.close()
    json.dump(dict(reg), open(f"{pd}/.reg.json", "w"))
    print(f"  pack-{i:02d}/web.parquet rows={got}/M={M}")
    return out, M

if __name__ == "__main__":
    t0 = time.time()
    # 1) shared core (+SA)
    core_files = sorted(glob.glob(f"{BUILD}/shared-core/*.parquet"))
    if core_files:
        stream(core_files, f"{SHARED}/core.parquet", "curated",
               sa_route=True, sa_out=f"{SHARED}/core_sa.parquet")
    # 2) legal (permissive) + legal_sa (juz rozdzielone przez subagenta)
    if os.path.exists(f"{BUILD}/legal/legal.parquet"):
        stream([f"{BUILD}/legal/legal.parquet"], f"{SHARED}/legal.parquet", "source")
        stream([f"{BUILD}/legal/legal_sa.parquet"], f"{SHARED}/legal_sa.parquet", "source")
    # 3) en
    if os.path.exists(f"{BUILD}/en/en.parquet"):
        stream([f"{BUILD}/en/en.parquet"], f"{SHARED}/en.parquet", "source")
    else:
        print("  PENDING en.parquet (subagent w toku)")
    # 4) pack web (tylko gotowe tagowane slice'y)
    for i in range(8):
        if os.path.exists(f"{WEB}/web-slice-{i}.tagged.parquet"):
            pack_web(i)
        else:
            print(f"  PENDING web-slice-{i}.tagged.parquet")
    print("assemble pass done in", round(time.time() - t0), "s")
