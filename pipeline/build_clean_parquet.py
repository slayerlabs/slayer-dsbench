"""Cleaned parquet (dla gate Wartownika/boilerprobe) + residual self-check.
Strip HARD-linii (line-level, jak .bin) -> cleaned text -> parquet. POTEM mierzy residual:
substring HARD-exact-markerow w cleaned (lapie EMBEDDED-in-line ktore line-strip omija) =
reconcile z Wartownika ~78k substring-union vs moje 53k line-level.
Usage: python build_clean_parquet.py [OUT.parquet]
"""
import sys, time, re
import pyarrow as pa, pyarrow.parquet as pq
sys.path.insert(0, r"C:/tmp/dsbench-monter")
from dsbench.checks.boilerplate import _classify

SRC = "C:/Projekty/Slayer/datasets/polish-dynaword-expansion/PREVIEW-korpus.parquet"
OUT = sys.argv[1] if len(sys.argv) > 1 else "C:/tmp/clean_v2_preview.parquet"
# exact-comment-cruft (nigdy legit proza) -> residual substring-scan; normalizacja: bez bialych znakow + lower
RES = ["odpowiedzusuń", "odpowiedzusun", "dodajkomentarz", "prześlijkomentarz",
       "przeslijkomentarz", "brakkomentarzy"]
_ws = re.compile(r"\s+")


def strip_hard(text):
    keep, n = [], 0
    for line in text.splitlines():
        if _classify(line) == "hard":
            n += 1
        else:
            keep.append(line)
    return "\n".join(keep), n


pf = pq.ParquetFile(SRC)
schema = pf.schema_arrow
w = pq.ParquetWriter(OUT, schema)
t0 = time.time(); ndoc = 0; stripped = 0
res_docs = {m: 0 for m in RES}; res_hits = {m: 0 for m in RES}
for batch in pf.iter_batches(batch_size=2000):
    d = batch.to_pydict()
    txt = d["text"]
    new = []
    for s in txt:
        if not s:
            new.append(s); continue
        c, n = strip_hard(s); stripped += n
        cn = _ws.sub("", c).lower()   # whole-doc, whitespace removed (upper-bound embedded)
        for m in RES:
            k = cn.count(m)
            if k:
                res_docs[m] += 1; res_hits[m] += k
        new.append(c); ndoc += 1
    d["text"] = new
    w.write_table(pa.Table.from_pydict(d, schema=schema))
w.close()
dt = time.time() - t0
print(f"DONE docs={ndoc:,} stripped_lines={stripped:,} out={OUT} [{dt:.0f}s]", flush=True)
print("=== RESIDUAL (substring w cleaned, whitespace-collapsed = upper-bound embedded) ===", flush=True)
tot = 0
for m in RES:
    print(f"  {m:20s} docs={res_docs[m]:>6,} hits={res_hits[m]:>7,}", flush=True)
    tot += res_docs[m]
print(f"  {'SUMA docs (z powt.)':20s} docs={tot:,}", flush=True)
