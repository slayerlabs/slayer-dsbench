#!/usr/bin/env python3
"""Baseline klasyfikatora rejestrow HPLT (bramka dla encodera, S1).
TF-IDF + LogisticRegression, stratified 5-fold CV. Raportuje macro-F1 (±95% CI z foldow)
+ per-rejestr precision/recall. Prog dla encodera: musi bic te liczby (kryt. obalenia C1).
Uzycie: python register_baseline.py [sciezka.jsonl]
"""
import sys, json, numpy as np
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import f1_score, precision_recall_fscore_support, classification_report

PATH = sys.argv[1] if len(sys.argv) > 1 else "/mnt/c/Projekty/Slayer/slayer-dsbench/eval_sets/hplt-register-silver-v1.jsonl"
GATE = {"dialog","qa","howto","nauka","literacki"}  # rejestry bramkowane (precision>=0.90 target)
MIN_N = 8

rows = [json.loads(l) for l in open(PATH, encoding="utf-8") if l.strip()]
X = [r["text"] for r in rows]; y = [r["register"] for r in rows]
cnt = Counter(y)
keep = {c for c,n in cnt.items() if n >= MIN_N}
dropped = {c:n for c,n in cnt.items() if n < MIN_N}
idx = [i for i,yy in enumerate(y) if yy in keep]
Xk = [X[i] for i in idx]; yk = [y[i] for i in idx]
print(f"n_total={len(rows)}  n_used={len(Xk)}  klasy_used={sorted(keep)}")
if dropped: print(f"POMINIETE (n<{MIN_N}, za cienkie na CV): {dropped}")

def mkpipe():
    return Pipeline([
        ("tf", TfidfVectorizer(ngram_range=(1,2), min_df=2, max_features=50000, sublinear_tf=True, strip_accents=None)),
        ("lr", LogisticRegression(max_iter=3000, class_weight="balanced", C=4.0)),
    ])

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
yp = cross_val_predict(mkpipe(), Xk, yk, cv=skf)
macro = f1_score(yk, yp, average="macro")
print(f"\n=== BASELINE TF-IDF+logreg (5-fold CV) ===")
print(f"macro-F1(pooled) = {macro:.3f}")
print(classification_report(yk, yp, digits=3, zero_division=0))

# per-rejestr precision (do bramki)
labels_sorted = sorted(keep)
P,R,F,S = precision_recall_fscore_support(yk, yp, labels=labels_sorted, zero_division=0)
print("=== per-rejestr precision (bramka: GATE>=0.90) ===")
for l,p,r,f,s in zip(labels_sorted,P,R,F,S):
    flag = " <GATE>" if l in GATE else ""
    print(f"  {l:16} P={p:.3f} R={r:.3f} F1={f:.3f} n={s}{flag}")

# per-fold macro -> CI
macros = []
for tr,te in skf.split(Xk,yk):
    pipe = mkpipe(); pipe.fit([Xk[i] for i in tr],[yk[i] for i in tr])
    pr = pipe.predict([Xk[i] for i in te])
    macros.append(f1_score([yk[i] for i in te], pr, average="macro"))
m = float(np.mean(macros)); ci = float(1.96*np.std(macros)/np.sqrt(len(macros)))
print(f"\nmacro-F1(per-fold) = {m:.3f} ±{ci:.3f} (95% CI)  folds={[round(x,3) for x in macros]}")

res = {"n_total":len(rows),"n_used":len(Xk),"dropped":dropped,"macro_f1_pooled":round(macro,4),
       "macro_f1_cv":round(m,4),"ci95":round(ci,4),
       "per_register":{l:{"precision":round(float(p),4),"recall":round(float(r),4),"n":int(s)}
                       for l,p,r,s in zip(labels_sorted,P,R,S)},
       "gate_registers":sorted(GATE),"model":"tfidf(1,2)+logreg(balanced,C=4)"}
open("/mnt/c/Projekty/Slayer/slayer-dsbench/eval_sets/baseline-register-tfidf.json","w",encoding="utf-8").write(json.dumps(res,ensure_ascii=False,indent=2))
print("\nzapis -> eval_sets/baseline-register-tfidf.json")
