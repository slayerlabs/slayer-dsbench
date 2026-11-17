#!/usr/bin/env python3
"""Kalibracja confidence-threshold per-rejestr dla embed(e5)+logreg.
Cel: czyste partycje — dla kazdego rejestru znajdz prog proby tau, przy ktorym precision>=TARGET,
i policz coverage (jaki % rekordow danego rejestru zostaje). Bez leakage (cross_val_predict proba).
Actionable dla mixu: ile diverse per-rejestr wyciagniemy z web przy czystosci >=0.90."""
import json, numpy as np
from collections import Counter
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict

PATH = "/mnt/c/Projekty/Slayer/slayer-dsbench/eval_sets/hplt-register-silver-v1.jsonl"
MODEL = "intfloat/multilingual-e5-base"
TARGET = 0.90
GATE = {"dialog","qa","howto","nauka","literacki"}; MIN_N = 8

rows = [json.loads(l) for l in open(PATH, encoding="utf-8") if l.strip()]
y_all = [r["register"] for r in rows]
cnt = Counter(y_all); keep = sorted({c for c,n in cnt.items() if n >= MIN_N})
idx = [i for i,yy in enumerate(y_all) if yy in keep]
X_txt = ["passage: " + rows[i]["text"][:1200] for i in idx]
y = np.array([y_all[i] for i in idx])
st = SentenceTransformer(MODEL)
X = st.encode(X_txt, batch_size=32, normalize_embeddings=True, show_progress_bar=False)

clf = LogisticRegression(max_iter=4000, class_weight="balanced", C=10.0)
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
proba = cross_val_predict(clf, X, y, cv=skf, method="predict_proba")
classes = list(clf.fit(X, y).classes_)
ci = {c:i for i,c in enumerate(classes)}
pred = np.array([classes[i] for i in proba.argmax(1)])
pmax = proba.max(1)

print(f"=== Kalibracja per-rejestr (target precision>={TARGET}) ===")
print(f"{'rejestr':16} tau  prec@tau  coverage  n_true  (bez progu: prec/rec)")
out = {}
for c in classes:
    ii = ci[c]
    # bez progu
    predc = pred == c; truec = y == c
    base_p = (predc & truec).sum() / max(predc.sum(),1)
    base_r = (predc & truec).sum() / max(truec.sum(),1)
    # sweep tau na probie klasy c wsrod predykowanych jako c
    best = None
    for tau in np.round(np.arange(0.30,0.981,0.02),3):
        sel = predc & (proba[:,ii] >= tau)
        if sel.sum() == 0: continue
        p = (sel & truec).sum() / sel.sum()
        cov = (sel & truec).sum() / max(truec.sum(),1)  # % prawdziwych c zachowanych
        if p >= TARGET:
            best = (tau, p, cov, sel.sum()); break
    g = " <GATE>" if c in GATE else ""
    if best:
        tau,p,cov,ns = best
        print(f"{c:16} {tau:.2f}  {p:.3f}    {cov:.2f}     {truec.sum():4}  ({base_p:.2f}/{base_r:.2f}){g}")
        out[c] = {"tau":float(tau),"precision":round(float(p),3),"coverage":round(float(cov),3),"n_true":int(truec.sum())}
    else:
        print(f"{c:16}  --   nieosiagalne przy tym n   n_true={truec.sum():4}  ({base_p:.2f}/{base_r:.2f}){g}")
        out[c] = {"tau":None,"reachable":False,"base_precision":round(float(base_p),3),"n_true":int(truec.sum())}
json.dump({"target":TARGET,"model":"e5+logreg","per_register":out},
          open("/mnt/c/Projekty/Slayer/slayer-dsbench/eval_sets/calibrate-register-e5.json","w",encoding="utf-8"),
          ensure_ascii=False, indent=2)
gate_ok = [c for c in GATE if out.get(c,{}).get("tau") is not None]
print(f"\nGATE osiagalne precision>={TARGET}: {gate_ok} / {sorted(GATE)}")
print("zapis -> eval_sets/calibrate-register-e5.json")
