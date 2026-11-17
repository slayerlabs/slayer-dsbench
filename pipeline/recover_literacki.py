#!/usr/bin/env python3
# Recovery literacki__ext (uszkodzony na dysku, 31/31 rg zle) -> odbudowa z 4 zrodel dynaword.
# Wzorzec: recover_nauka_enc.py. exact-dedup(sha256 norm) + decontam(eval 8-gram) + ATOMIC write_table.
# Per-row is_share_alike (wikisource/wolne_lektury=SA) -> assemble routuje do core_sa.
import os, re, json, time, hashlib
import pyarrow as pa, pyarrow.parquet as pq
import tiktoken
t0 = time.time()
def log(m): print(f"[{time.time()-t0:7.1f}s] {m}", flush=True)
DW = "/mnt/c/Projekty/datasets/polish-dynaword/data"
OUT = "/mnt/c/Projekty/datasets/build/shared-core/literacki__ext.parquet"
ENC = tiktoken.get_encoding("cl100k_base")
WS = re.compile(r"\s+")
def norm(t): return WS.sub(" ", t.lower()).strip()
def shingles8(t):
    w = norm(t).split(); n = max(1, len(w) - 7); step = max(1, n // 32)
    return {hashlib.blake2b(" ".join(w[i:i+8]).encode(), digest_size=8).digest() for i in range(0, n, step)}

log("decontam: build eval 8-gram set")
EVAL = set()
def add_texts(txts):
    for t in txts:
        if not t: continue
        w = norm(t).split()
        for i in range(0, max(1, len(w) - 7)):
            EVAL.add(hashlib.blake2b(" ".join(w[i:i+8]).encode(), digest_size=8).digest())
try:
    from datasets import load_dataset
    for ds in ["sdadas/8tags", "allegro/klej-polemo2-in", "allegro/klej-polemo2-out"]:
        try:
            d = load_dataset(ds)
            for sp in d:
                c = next((x for x in d[sp].column_names if d[sp].features[x].dtype == "string"), None)
                if c: add_texts(d[sp][c])
        except Exception as e: log(f"  eval {ds} skip {e}")
except Exception as e: log(f"decontam load fail {e}")
log(f"eval 8grams={len(EVAL)}")

def load_texts(path):
    pf = pq.ParquetFile(path); cols = pf.schema.names
    tc = next((c for c in ["text", "content", "tekst", "body"] if c in cols), cols[0])
    for b in pf.iter_batches(batch_size=2000, columns=[tc]):
        for v in b.column(0).to_pylist():
            if v: yield v

DOCS, SRCS, LICS, SAS = [], [], [], []
seen = set()
stats = []
# (key, path, license, is_share_alike)
SOURCES = [
    ("wolne_lektury", f"{DW}/wolne_lektury/wolne_lektury.parquet", "CC-BY-SA-4.0", True),
    ("1000_novels",   f"{DW}/1000_novels/1000_novels.parquet",     "CC-BY-4.0",    False),
    ("eltec_pol",     f"{DW}/eltec_pol/eltec_pol.parquet",         "CC-BY-4.0",    False),
    ("wikisource",    f"{DW}/wikisource/wikisource.parquet",       "CC-BY-SA-3.0", True),
]
for key, path, lic, sa in SOURCES:
    if not os.path.exists(path):
        log(f"{key} BRAK {path} - pomijam"); stats.append({"key": key, "present": False}); continue
    nin = nkeep = ndup = ndec = tok = 0
    for t in load_texts(path):
        nin += 1
        h = hashlib.sha256(norm(t).encode()).digest()
        if h in seen: ndup += 1; continue
        seen.add(h)
        sh = shingles8(t)
        if sh and len(sh & EVAL) >= 1: ndec += 1; continue
        DOCS.append(t); SRCS.append(key); LICS.append(lic); SAS.append(sa)
        nkeep += 1; tok += len(ENC.encode(t))
        if nin % 50000 == 0: log(f"  {key}: in={nin} keep={nkeep} dup={ndup} dec={ndec}")
    log(f"{key} DONE in={nin} keep={nkeep} dup={ndup} dec={ndec} tok={tok}")
    stats.append({"key": key, "license": lic, "is_share_alike": sa, "in": nin,
                  "kept": nkeep, "exact_dup": ndup, "decon": ndec, "tokens_cl100k": tok})

tb = pa.table({
    "document_id": [f"literacki_ext-{i:07d}" for i in range(len(DOCS))],
    "source_id": SRCS, "text": DOCS, "register": ["literacki"] * len(DOCS),
    "license": LICS, "is_share_alike": SAS, "provenance": ["dynaword"] * len(DOCS)})
pq.write_table(tb, OUT, compression="zstd")  # ATOMIC: footer gwarantowany
tot = sum(s.get("tokens_cl100k", 0) for s in stats)
json.dump({"stats": stats, "total_tokens_cl100k": tot, "rows": len(DOCS)},
          open("/mnt/c/Projekty/datasets/build/recover-literacki-stats.json", "w"), ensure_ascii=False, indent=2)
log(f"ALL DONE rows={len(DOCS)} tok={tot} -> {OUT}")
print("RECOVER-LITERACKI:", tot, "cl100k,", len(DOCS), "docs")
