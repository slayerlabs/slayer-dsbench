"""Run-A corpus: v1 HPLT-expansion MINUS HARD web-boilerplate (line-strip) -> uint16 .bin + val-split.
Identyczny builder jak v1 (tokenize_corpus.py): tokenizer ppuzio/dynaword-32k, eot=0 SUFFIX per doc,
uint16 raw stream (bez headera) -> kompatybilny z train_125m.py (np.memmap uint16).
Jedyna zmiana vs v1 = strip HARD boilerplate-linii (checks/boilerplate._classify, single source) +
val-split 1/200 (v1 nie mial). => czysty one-variable (rozmiar ~bez zmian, tylko boilerplate usuniety).
Usage: python build_clean_corpus.py TRAIN_OUT.bin VAL_OUT.bin
"""
import sys, time, numpy as np, pyarrow.parquet as pq
from tokenizers import Tokenizer
sys.path.insert(0, r"C:/tmp/dsbench-monter")
from dsbench.checks.boilerplate import _classify   # HARD/SOFT tier (Wartownik), zwalidowany FP-safe

TOK = "C:/Projekty/Slayer/tokenizer/ppuzio/tokenizers/dynaword-32k/tokenizer.json"
SRC = "C:/Projekty/Slayer/datasets/polish-dynaword-expansion/PREVIEW-korpus.parquet"  # dokladnie zrodlo v1
TRAIN_OUT = sys.argv[1] if len(sys.argv) > 1 else "C:/tmp/clean_train_32k.bin"
VAL_OUT = sys.argv[2] if len(sys.argv) > 2 else "C:/tmp/clean_val_32k.bin"
VAL_EVERY = 200
BATCH = 2000

tok = Tokenizer.from_file(TOK)
eot = tok.token_to_id("<|endoftext|>")
assert eot is not None
print(f"tokenizer vocab={tok.get_vocab_size()} eot_id={eot}", flush=True)

def strip_hard(text):
    """Usun linie HARD-boilerplate; zachowaj reszte (SOFT + tresc). Zwroc (cleaned, n_stripped)."""
    keep, n = [], 0
    for line in text.splitlines():
        if _classify(line) == "hard":
            n += 1
        else:
            keep.append(line)
    return "\n".join(keep), n

pf = pq.ParquetFile(SRC)
ft = open(TRAIN_OUT, "wb")
val_ids = []
t0 = time.time()
ntok_tr = ndoc = di = stripped = emptied = 0
last = 0
for batch in pf.iter_batches(batch_size=BATCH, columns=["text"]):
    raw = [t.as_py() for t in batch["text"]]
    cleaned = []
    for s in raw:
        if not s:
            continue
        c, n = strip_hard(s)
        stripped += n
        c = c.strip()
        if not c:
            emptied += 1
            continue
        cleaned.append(c)
    if not cleaned:
        continue
    encs = tok.encode_batch(cleaned)
    tr_arrs = []
    for e in encs:
        ids = e.ids
        ids.append(eot)
        if di % VAL_EVERY == 0:
            val_ids.extend(ids)
        else:
            tr_arrs.append(np.asarray(ids, dtype=np.uint16))
        di += 1
    if tr_arrs:
        a = np.concatenate(tr_arrs)
        a.tofile(ft)
        ntok_tr += int(a.size)
    ndoc += len(cleaned)
    if ndoc - last >= 100000:
        last = ndoc
        dt = time.time() - t0
        print(f"docs={ndoc:,} train_tok={ntok_tr/1e6:.1f}M val_tok={len(val_ids)/1e6:.2f}M "
              f"stripped_lines={stripped:,} emptied={emptied} {ntok_tr/max(1,dt)/1e3:.0f}k tok/s [{dt:.0f}s]", flush=True)
ft.close()
np.asarray(val_ids, dtype=np.uint16).tofile(VAL_OUT)
dt = time.time() - t0
print(f"\nDONE docs={ndoc:,} train_tok={ntok_tr:,} ({ntok_tr/1e6:.1f}M, {ntok_tr*2/1e9:.2f}GB) "
      f"val_tok={len(val_ids):,} ({len(val_ids)/1e6:.2f}M) stripped_lines={stripped:,} emptied_docs={emptied} "
      f"[{dt:.0f}s]\ntrain={TRAIN_OUT}\nval={VAL_OUT}", flush=True)
