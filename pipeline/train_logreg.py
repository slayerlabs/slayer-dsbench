"""Trenuje logreg na osadzeniach silver (regcls venv, sklearn) -> eksport coef/intercept/classes do npz.
Inferencja pozniej pure-numpy w rocm-torch (bez sklearn tam)."""
import json, numpy as np
from collections import Counter
from sklearn.linear_model import LogisticRegression
ES = "/mnt/c/Projekty/Slayer/slayer-dsbench/eval_sets"
X = np.load(f"{ES}/silver_emb.npy")
y = json.load(open(f"{ES}/silver_labels.json"))
cnt = Counter(y); keep = {c for c, n in cnt.items() if n >= 8}
idx = [i for i, v in enumerate(y) if v in keep]
Xk = X[idx]; yk = [y[i] for i in idx]
clf = LogisticRegression(max_iter=5000, class_weight="balanced", C=10.0).fit(Xk, yk)
np.savez(f"{ES}/logreg_coef.npz", coef=clf.coef_.astype(np.float32),
         intercept=clf.intercept_.astype(np.float32), classes=np.array(clf.classes_))
print("logreg klasy:", list(clf.classes_), "| n=", len(yk))
