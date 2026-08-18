"""Run-A corpus: v1 HPLT-expansion MINUS web-boilerplate -> uint16 .bin + val-split.
Identyczny builder jak v1 (tokenize_corpus.py): tokenizer ppuzio/dynaword-32k, eot=0 SUFFIX per doc,
uint16 raw stream (bez headera) -> kompatybilny z train_125m.py (np.memmap uint16). val-split 1/200 (v1 nie mial).

Czyszczenie boilerplate (2 warstwy, po odkryciu residualu 394k embedded OdpowiedzUsun):
  1. SPAN-strip (substring, zero-FP): "Odpowiedz Usun" (Blogger comment-mod para; dwa imperatywy
     obok siebie NIE wystepuja w naturalnej prozie) -> lapie EMBEDDED/concatenated (line-strip omijal).
  2. LINE-strip (cala linia == HARD marker, checks/boilerplate._classify) -> reszta comment/nav-cruft.
=> pure one-variable (tylko boilerplate; SOFT + tresc zachowane).
Usage: python build_clean_corpus.py TRAIN_OUT.bin VAL_OUT.bin
"""
import sys, time, re, numpy as np, pyarrow.parquet as pq
from tokenizers import Tokenizer
sys.path.insert(0, r"C:/tmp/dsbench-monter")
from dsbench.checks.boilerplate import _classify   # HARD line-tier (Wartownik), FP-safe

TOK = "C:/Projekty/Slayer/tokenizer/ppuzio/tokenizers/dynaword-32k/tokenizer.json"
SRC = "C:/Projekty/Slayer/datasets/polish-dynaword-expansion/PREVIEW-korpus.parquet"  # dokladnie zrodlo v1
TRAIN_OUT = sys.argv[1] if len(sys.argv) > 1 else "C:/tmp/clean_train_32k.bin"
VAL_OUT = sys.argv[2] if len(sys.argv) > 2 else "C:/tmp/clean_val_32k.bin"
VAL_EVERY = 200
BATCH = 2000
# zero-FP substring comment-cruft (embedded/concatenated): "Odpowiedz Usun/Usuń", <=3 whitespace/newline
SPAN_RE = re.compile(r"odpowiedz\s{0,3}usu[nń]", re.I)

tok = Tokenizer.from_file(TOK)
eot = tok.token_to_id("<|endoftext|>")
assert eot is not None
print(f"tokenizer vocab={tok.get_vocab_size()} eot_id={eot}", flush=True)


def strip_boiler(text):
    """SPAN-strip embedded OdpowiedzUsun (zero-FP) + LINE-strip whole-line HARD. Zwroc (cleaned, n_line, n_span)."""
    text, n_span = SPAN_RE.subn(" ", text)
    keep, n_line = [], 0
    for line in text.splitlines():
        if _classify(line) == "hard":
            n_line += 1
        else:
            keep.append(line)
    return "\n".join(keep), n_line, n_span


pf = pq.ParquetFile(SRC)
ft = open(TRAIN_OUT, "wb")
val_ids = []
t0 = time.time()
ntok_tr = ndoc = di = line_stripped = span_stripped = emptied = 0
last = 0
for batch in pf.iter_batches(batch_size=BATCH, columns=["text"]):
    raw = [t.as_py() for t in batch["text"]]
    cleaned = []
    for s in raw:
        if not s:
            continue
        c, nl, nsp = strip_boiler(s)
        line_stripped += nl; span_stripped += nsp
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
              f"line={line_stripped:,} span={span_stripped:,} emptied={emptied} "
              f"{ntok_tr/max(1,dt)/1e3:.0f}k tok/s [{dt:.0f}s]", flush=True)
ft.close()
np.asarray(val_ids, dtype=np.uint16).tofile(VAL_OUT)
dt = time.time() - t0
print(f"\nDONE docs={ndoc:,} train_tok={ntok_tr:,} ({ntok_tr/1e6:.1f}M, {ntok_tr*2/1e9:.2f}GB) "
      f"val_tok={len(val_ids):,} ({len(val_ids)/1e6:.2f}M) line_stripped={line_stripped:,} "
      f"span_stripped={span_stripped:,} emptied_docs={emptied} [{dt:.0f}s]\ntrain={TRAIN_OUT}\nval={VAL_OUT}", flush=True)
