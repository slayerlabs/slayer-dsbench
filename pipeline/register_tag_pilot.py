#!/usr/bin/env python3
"""PILOT bulk-tag: trenuj embed(e5)+logreg na silver-v1, otaguj probke web-slice-0 (N doc),
zastosuj per-rejestr confidence-threshold (calibrate-register-e5.json) -> CZYSTE partycje (>=0.90 precision)
+ reszta -> kwarantanna 'niepewne'. Raport realnych wolumenow per-rejestr na faktycznym web.
Dowod pipeline + liczby dla decyzji mixu. NIE full-24B (to GPU + go Arka). Uzycie: python register_tag_pilot.py [N]"""
import sys, json, numpy as np, pyarrow.parquet as pq, pyarrow as pa
from collections import Counter
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
SILVER = "/mnt/c/Projekty/Slayer/slayer-dsbench/eval_sets/hplt-register-silver-v1.jsonl"
CALIB = "/mnt/c/Projekty/Slayer/slayer-dsbench/eval_sets/calibrate-register-e5.json"
SLICE = "/mnt/c/Projekty/datasets/build/web/web-slice-0.parquet"
OUTDIR = "/mnt/c/Projekty/Slayer/slayer-dsbench/datasets/hplt-registers-pilot"
MODEL = "intfloat/multilingual-e5-base"; MIN_N = 8

rows = [json.loads(l) for l in open(SILVER, encoding="utf-8") if l.strip()]
yb = Counter(r["register"] for r in rows); keep = {c for c,n in yb.items() if n >= MIN_N}
tr = [(r["text"], r["register"]) for r in rows if r["register"] in keep]
calib = json.load(open(CALIB, encoding="utf-8"))["per_register"]
tau = {c: (calib.get(c, {}).get("tau") or 0.99) for c in keep}

print(f"laduje {MODEL}; train n={len(tr)}; taguje N={N} z web-slice-0 ...", flush=True)
st = SentenceTransformer(MODEL)
Xtr = st.encode(["passage: " + t[:1200] for t, _ in tr], batch_size=32, normalize_embeddings=True, show_progress_bar=False)
clf = LogisticRegression(max_iter=4000, class_weight="balanced", C=10.0).fit(Xtr, [y for _, y in tr])
classes = list(clf.classes_); ci = {c: i for i, c in enumerate(classes)}

pf = pq.ParquetFile(SLICE)
texts, ids = [], []
need = N
for rg in range(pf.num_row_groups):
    if need <= 0: break
    t = pf.read_row_group(rg, columns=["text", "document_id"])
    tx = t.column("text").to_pylist(); di = t.column("document_id").to_pylist()
    take = min(need, len(tx)); texts += tx[:take]; ids += di[:take]; need -= take
print(f"wczytano {len(texts)} doc z slice", flush=True)
Xin = st.encode(["passage: " + (x or "")[:1200] for x in texts], batch_size=64, normalize_embeddings=True, show_progress_bar=False)
proba = clf.predict_proba(Xin)
amax = proba.argmax(1); pmax = proba.max(1)
reg, keep_mask = [], []
for i in range(len(texts)):
    c = classes[amax[i]]
    if proba[i, ci[c]] >= tau[c]:
        reg.append(c); keep_mask.append(True)
    else:
        reg.append("niepewne"); keep_mask.append(False)
dist_clean = Counter(r for r, k in zip(reg, keep_mask) if k)
n_clean = sum(keep_mask)
print(f"\n=== PILOT TAG web-slice-0, N={len(texts)} ===")
print(f"czyste (>=prog): {n_clean} ({100*n_clean/len(texts):.1f}%) · niepewne(kwarantanna): {len(texts)-n_clean} ({100*(len(texts)-n_clean)/len(texts):.1f}%)")
print("czyste partycje per-rejestr (i ekstrapolacja na 2.39B slice, potem ×10):")
slice_tok = 2392014542
for c, n in dist_clean.most_common():
    frac = n/len(texts); est_slice = frac*slice_tok/1e9
    print(f"  {c:16} {n:6}  {100*frac:5.1f}%  ~{est_slice:.2f}B/slice  ~{est_slice*10:.1f}B/10")
# zapis register-tagged parquet (tylko czyste, enum-valid) + karta
import os; os.makedirs(OUTDIR, exist_ok=True)
recs = [{"document_id": ids[i], "source_id": "hplt_v3_pl:bin8", "text": texts[i],
         "register": reg[i], "license": "CC0-1.0", "classified_by": "e5+logreg+thr",
         "provenance": "web-slice-0"} for i in range(len(texts)) if keep_mask[i]]
with open(f"{OUTDIR}/sample.jsonl", "w", encoding="utf-8") as f:
    for r in recs[:2000]: f.write(json.dumps(r, ensure_ascii=False) + "\n")  # sample dla dsbench karty
json.dump({"N": len(texts), "n_clean": n_clean, "clean_pct": round(100*n_clean/len(texts),1),
           "dist_clean": dict(dist_clean), "tau": {k: round(v,2) for k,v in tau.items()}},
          open("/mnt/c/Projekty/Slayer/slayer-dsbench/eval_sets/pilot-tag-slice0.json","w",encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(f"\nzapis: {OUTDIR}/sample.jsonl (2k dla karty) + eval_sets/pilot-tag-slice0.json")
