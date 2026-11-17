#!/usr/bin/env python3
"""Finalize slayer-pl-8x3b: manifesty (sha256 + tokeny + rozklad rejestrow + SA), sample.jsonl,
aktualizacja dataset.json. Uruchamiane po assemble.py (wszystkie parquet istnieja)."""
import glob, os, json, hashlib, time
from collections import Counter
import pyarrow.parquet as pq

DS = "/mnt/c/Projekty/datasets/slayer-pl-8x3b"
BUILD = "/mnt/c/Projekty/datasets/build"
SHARED = f"{DS}/shared"
WS = json.load(open(f"{BUILD}/web-backbone-stats.json"))
SLICE_TOK, SLICE_DOCS = WS["slice_tok"], WS["slice_docs"]
# core token total: 4 nieuszkodzone rejestry z shared-core-FINAL + odbudowany literacki (ext recover + base)
import tiktoken as _tk
_enc = _tk.get_encoding("cl100k_base")
_lit_ext = json.load(open(f"{BUILD}/recover-literacki-stats.json"))["total_tokens_cl100k"]
_lit_base = 0
for _b in pq.ParquetFile(f"{BUILD}/shared-core/literacki.parquet").iter_batches(batch_size=2000, columns=["text"]):
    for _t in _b.column(0).to_pylist():
        _lit_base += len(_enc.encode(_t or ""))
CORE_TOK = 873502471 + 735149034 + 664726709 + 277043698 + _lit_base + _lit_ext  # qa+enc+nauka+news+literacki(nowy)
LEG = json.load(open(f"{BUILD}/legal/legal.stats.json"))
EN = json.load(open(f"{BUILD}/en/en.stats.json"))

def sha256(path, buf=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(buf), b""):
            h.update(b)
    return h.hexdigest()

def rows_regs(path):
    pf = pq.ParquetFile(path); n = pf.metadata.num_rows; c = Counter()
    for b in pf.iter_batches(batch_size=20000, columns=["register"]):
        c.update(b.column("register").to_pylist())
    return n, dict(c)

def sample(path, k=5):
    pf = pq.ParquetFile(path)
    b = next(pf.iter_batches(batch_size=k)).to_pylist()
    return b[:k]

def finfo(path, tokens):
    n, regs = rows_regs(path)
    return {"plik": os.path.relpath(path, DS), "wiersze": n, "tokeny_cl100k": int(tokens),
            "sha256": sha256(path), "rozklad_rejestrow": regs}

if __name__ == "__main__":
    t0 = time.time()
    core_n = pq.ParquetFile(f"{SHARED}/core.parquet").metadata.num_rows
    core_sa_n = pq.ParquetFile(f"{SHARED}/core_sa.parquet").metadata.num_rows
    tot = core_n + core_sa_n
    core_tok = round(CORE_TOK * core_n / tot); core_sa_tok = CORE_TOK - core_tok
    shared = {
        "core.parquet": finfo(f"{SHARED}/core.parquet", core_tok),
        "core_sa.parquet": finfo(f"{SHARED}/core_sa.parquet", core_sa_tok),
        "legal.parquet": finfo(f"{SHARED}/legal.parquet", LEG["tokens_permissive"]),
        "legal_sa.parquet": finfo(f"{SHARED}/legal_sa.parquet", LEG["tokens_sa"]),
        "en.parquet": finfo(f"{SHARED}/en.parquet", EN["tokens_cl100k"]),
    }
    json.dump({"komponenty": shared, "uwaga": "wspolny backbone referencjonowany przez 8 zbiorow; "
               "tokeny rdzenia prorata po wierszach, legal/en exact (tiktoken), SA w osobnych partycjach"},
              open(f"{SHARED}/manifest.json", "w"), ensure_ascii=False, indent=2)
    print("shared manifest OK", round(time.time() - t0), "s")

    packs = []
    for i in range(8):
        pd = f"{DS}/pack-{i:02d}"; wp = f"{pd}/web.parquet"
        n, regs = rows_regs(wp)
        wtok = round(SLICE_TOK[i] * n / SLICE_DOCS[i])
        man = {
            "zbior": f"pack-{i:02d}", "jednostka": "tokens_cl100k",
            "web": {"plik": "web.parquet", "wiersze": n, "tokeny_cl100k": wtok,
                    "sha256": sha256(wp), "rozklad_rejestrow": regs, "licencja": "CC0-1.0"},
            "referencje_shared": {
                "rdzen": "../shared/core.parquet", "rdzen_sa": "../shared/core_sa.parquet",
                "legal": "../shared/legal.parquet", "legal_sa": "../shared/legal_sa.parquet",
                "en": "../shared/en.parquet"},
            "wagi_probkowania": {"web": 0.63, "rdzen": 0.19, "legal": 0.08, "en": 0.10},
            "budzet_docelowy_tokeny_mld": 3.0,
            "uwaga": "web rozlaczny (ten zbior); rdzen/legal/en wspolne (shared/); wagi = proporcje probkowania"}
        json.dump(man, open(f"{pd}/manifest.json", "w"), ensure_ascii=False, indent=2)
        with open(f"{pd}/sample.jsonl", "w", encoding="utf-8") as f:
            for r in sample(wp):
                r["text"] = (r["text"] or "")[:800]
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        os.path.exists(f"{pd}/.reg.json") and os.remove(f"{pd}/.reg.json")
        packs.append({"zbior": f"pack-{i:02d}", "web_wiersze": n, "web_tokeny_cl100k": wtok})
        print(f"pack-{i:02d} manifest OK ({n} web rows)")

    # dataset.json: realized totals + status
    dj = json.load(open(f"{DS}/dataset.json", encoding="utf-8"))
    web_tot = sum(p["web_tokeny_cl100k"] for p in packs)
    dj["realizacja"] = {
        "web_tokeny_cl100k": web_tot, "rdzen_tokeny_cl100k": CORE_TOK,
        "legal_permissive_cl100k": LEG["tokens_permissive"], "legal_sa_cl100k": LEG["tokens_sa"],
        "en_cl100k": EN["tokens_cl100k"], "zbiory": packs,
        "backbone_fizyczny_tokeny_cl100k": web_tot + CORE_TOK + LEG["tokens_permissive"] + LEG["tokens_sa"] + EN["tokens_cl100k"]}
    dj["status"] = "zbudowany (wstepnie przeczyszczony; near-dup web w toku)"
    json.dump(dj, open(f"{DS}/dataset.json", "w"), ensure_ascii=False, indent=2)
    print("dataset.json OK; web_tot_cl100k", web_tot, "| total", round(time.time() - t0), "s")
