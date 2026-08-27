#!/usr/bin/env python3
"""Kandydat klasyfikatora: LOKALNY encoder (sentence-transformers, offline) + LogisticRegression.
Bez LM Studio (WSL go nie widzi). Apple-to-apple z baseline TF-IDF (5-fold CV, MIN_N=8).
Model: intfloat/multilingual-e5-base (prefix 'passage: '). Uzycie: python register_embed_local.py"""
import json, numpy as np
from collections import Counter
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import f1_score, precision_recall_fscore_support, classification_report

PATH = "/mnt/c/Projekty/Slayer/slayer-dsbench/eval_sets/hplt-register-silver-v1.jsonl"
MODEL = "intfloat/multilingual-e5-base"
GATE = {"dialog","qa","howto","nauka","literacki"}; MIN_N = 8

rows = [json.loads(l) for l in open(PATH, encoding="utf-8") if l.strip()]
y_all = [r["register"] for r in rows]
cnt = Counter(y_all); keep = {c for c,n in cnt.items() if n >= MIN_N}
idx = [i for i,yy in enumerate(y_all) if yy in keep]
X_txt = ["passage: " + rows[i]["text"][:1200] for i in idx]; y = [y_all[i] for i in idx]
print(f"n_used={len(y)} klasy={sorted(keep)}  laduje {MODEL} ...", flush=True)
st = SentenceTransformer(MODEL)
X = st.encode(X_txt, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
print("embed shape:", X.shape, flush=True)

clf = lambda: LogisticRegression(max_iter=4000, class_weight="balanced", C=10.0)
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
yp = cross_val_predict(clf(), X, y, cv=skf)
macro = f1_score(y, yp, average="macro")
print(f"\n=== EMBED-LOCAL (multilingual-e5-base)+logreg 5-fold CV ===")
print(f"macro-F1(pooled) = {macro:.3f}")
print(classification_report(y, yp, digits=3, zero_division=0))
labs = sorted(keep)
P,R,F,S = precision_recall_fscore_support(y, yp, labels=labs, zero_division=0)
print("=== per-rejestr precision (GATE>=0.90) ===")
for l,p,r,s in zip(labs,P,R,S):
    print(f"  {l:16} P={p:.3f} R={r:.3f} n={s}{'  <GATE>' if l in GATE else ''}")
macros=[]
for tr,te in skf.split(X,y):
    m=clf().fit(X[tr],[y[i] for i in tr]); pr=m.predict(X[te])
    macros.append(f1_score([y[i] for i in te],pr,average="macro"))
mm=float(np.mean(macros)); ci=float(1.96*np.std(macros)/np.sqrt(len(macros)))
print(f"\nmacro-F1(per-fold) = {mm:.3f} +-{ci:.3f} (95% CI)  vs baseline TF-IDF 0.388+-0.057")
verdict = "BIJE baseline (CI rozlaczne)" if (mm-ci) > (0.388+0.057) else ("lepszy ale CI zachodzi" if mm>0.388 else "NIE bije")
print(f"WERDYKT vs prog: {verdict}")
json.dump({"model":"multilingual-e5-base+logreg","n_used":len(y),"macro_f1_pooled":round(macro,4),
           "macro_f1_cv":round(mm,4),"ci95":round(ci,4),"baseline_tfidf":0.388,"baseline_ci":0.057,
           "verdict":verdict,
           "per_register":{l:{"precision":round(float(p),4),"recall":round(float(r),4),"n":int(s)}
                           for l,p,r,s in zip(labs,P,R,S)}},
          open("/mnt/c/Projekty/Slayer/slayer-dsbench/eval_sets/embed-register-e5.json","w",encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("zapis -> eval_sets/embed-register-e5.json")
