"""assemble_multisource.py — złóż multi-source korpus (HPLT-clean + curated) wg ratio -> uint16 .bin + val.
Tokenizer ppuzio/dynaword-32k (vocab32000, eot=0 SUFFIX/doc), val 1/200. Kompatybilny z train_125m.py.
- HPLT: PREVIEW-korpus + boilerplate-strip (SPAN OdpowiedzUsun + LINE HARD) — jak Run-A.
- Curated: pre-expansion-snapshot (REALNE parquety). non-legal (wiki/książki/nauka) domyślnie;
  legal (eurlex/parliament/dzu) tylko do --legal-tok CAP (bez capa zdominuje, 2.99B).
Sampling losowy przy treningu (get_batch randint) => concat wystarcza, NIE pre-shuffle (Hart zweryfikował).
Usage: python assemble_multisource.py --hplt-tok 1.0e9 --curated-tok 1.0e9 --legal-tok 0 --out-train T.bin --out-val V.bin
"""
import argparse, sys, time, re, random, numpy as np, pyarrow.parquet as pq
from tokenizers import Tokenizer
sys.path.insert(0, r"C:/tmp/dsbench-monter")
from dsbench.checks.boilerplate import _classify

TOK = "C:/Projekty/Slayer/tokenizer/ppuzio/tokenizers/dynaword-32k/tokenizer.json"
HPLT_SRC = "C:/Projekty/Slayer/datasets/polish-dynaword-expansion/PREVIEW-korpus.parquet"
BASE = r"C:/Projekty/datasets/polish-dynaword.pre-expansion-snapshot/data"
HPLT_AVAIL = 1.3525e9   # zmierzony clean-HPLT (~32k, po boilerplate-strip) — do keep_prob subsample
random.seed(42)         # reprodukowalny subsample
NONLEGAL = ["wikisource", "wikipedia", "wolne_lektury", "1000_novels", "wikiquote",
            "eltec_pol", "wikivoyage", "wikibooks", "wikinews"]
LEGAL = ["dziennik_ustaw", "parliamentary", "eurlex"]   # cap-only
SPAN_RE = re.compile(r"odpowiedz\s{0,3}usu[nń]", re.I)
VAL_EVERY = 200
BATCH = 2000

tok = Tokenizer.from_file(TOK)
EOT = tok.token_to_id("<|endoftext|>")


def strip_boiler(text):
    text = SPAN_RE.sub(" ", text)
    return "\n".join(l for l in text.splitlines() if _classify(l) != "hard")


def doc_stream_hplt(keep_prob):
    """PREVIEW-korpus + boilerplate-strip; LOSOWY subsample (keep_prob) -> unika bias binów HPLT (5-9)."""
    pf = pq.ParquetFile(HPLT_SRC)
    for b in pf.iter_batches(batch_size=BATCH, columns=["text"]):
        for x in b.column("text"):
            s = x.as_py()
            if not s or random.random() >= keep_prob:
                continue
            c = strip_boiler(s).strip()
            if c:
                yield c


def doc_stream_source(name):
    f = f"{BASE}/{name}/{name}.parquet"
    pf = pq.ParquetFile(f)
    for b in pf.iter_batches(batch_size=BATCH, columns=["text"]):
        for x in b.column("text"):
            s = x.as_py()
            if s and s.strip():
                yield s.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hplt-tok", type=float, required=True)
    ap.add_argument("--curated-tok", type=float, required=True, help="cel non-legal curated (32k tok)")
    ap.add_argument("--legal-tok", type=float, default=0.0, help="CAP legal (0=bez legal)")
    ap.add_argument("--per-source-cap", type=float, default=0.45, help="max frakcja curated z jednego źródła")
    ap.add_argument("--out-train", required=True)
    ap.add_argument("--out-val", required=True)
    a = ap.parse_args()
    print(f"tokenizer vocab={tok.get_vocab_size()} eot={EOT} | cele: HPLT={a.hplt_tok/1e9:.2f}B "
          f"curated={a.curated_tok/1e9:.2f}B legal_cap={a.legal_tok/1e9:.2f}B", flush=True)

    ft = open(a.out_train, "wb")
    val_ids = []
    di = [0]; ntr = [0]; t0 = time.time()

    def emit(text_iter, budget, label, per_src_cap=None):
        """Tokenizuj z iteratora aż osiągniesz budget (32k tok). Zwróć zużyte tok."""
        used = 0; buf = []; ndoc = 0
        def flush():
            nonlocal used
            if not buf:
                return
            for e in tok.encode_batch(buf):
                ids = e.ids; ids.append(EOT)
                if di[0] % VAL_EVERY == 0:
                    val_ids.extend(ids)
                else:
                    np.asarray(ids, dtype=np.uint16).tofile(ft); ntr[0] += len(ids)
                used += len(ids); di[0] += 1
            buf.clear()
        for s in text_iter:
            buf.append(s); ndoc += 1
            if len(buf) >= BATCH:
                flush()
                if used >= budget:
                    break
        flush()
        print(f"  [{label}] docs={ndoc:,} tok={used/1e6:.0f}M [{time.time()-t0:.0f}s]", flush=True)
        return used

    # 1. HPLT-clean
    hplt_keep = min(1.0, a.hplt_tok / HPLT_AVAIL)
    emit(doc_stream_hplt(hplt_keep), a.hplt_tok, f"HPLT-clean(keep={hplt_keep:.2f})")
    # 2. curated non-legal — round-robin-ish: bierz źródła po kolei z per-source cap
    cap = a.curated_tok * a.per_source_cap
    got = 0
    for name in NONLEGAL:
        if got >= a.curated_tok:
            break
        budget = min(cap, a.curated_tok - got)
        got += emit(doc_stream_source(name), budget, f"curated:{name}")
    # 3. legal do capa (opcjonalnie)
    if a.legal_tok > 0:
        gl = 0
        for name in LEGAL:
            if gl >= a.legal_tok:
                break
            gl += emit(doc_stream_source(name), min(a.legal_tok - gl, a.legal_tok * 0.5), f"legal:{name}")

    ft.close()
    np.asarray(val_ids, dtype=np.uint16).tofile(a.out_val)
    dt = time.time() - t0
    print(f"\nDONE train_tok={ntr[0]:,} ({ntr[0]/1e9:.3f}B, {ntr[0]*2/1e9:.2f}GB) val_tok={len(val_ids):,} "
          f"docs={di[0]:,} [{dt:.0f}s]\ntrain={a.out_train}\nval={a.out_val}", flush=True)


if __name__ == "__main__":
    main()
