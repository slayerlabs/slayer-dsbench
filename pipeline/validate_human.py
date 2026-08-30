#!/usr/bin/env python3
"""Walidacja AT1.1: e5-klasyfikator (train na silver) vs auto-labeler vs HUMAN-gold (batch-04, 30 doc).
Rozstrzyga czy klasyfikator jest realnie dobry czy powiela auto-labeler."""
import json, numpy as np
from collections import Counter
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression

SILVER="/mnt/c/Projekty/Slayer/slayer-dsbench/eval_sets/hplt-register-silver-v1.jsonl"
CMP="/mnt/c/tmp/batch04_compare.json"
MODEL="intfloat/multilingual-e5-base"; MIN_N=8

sv=[json.loads(l) for l in open(SILVER,encoding="utf-8") if l.strip()]
yb=Counter(r["register"] for r in sv); keep={c for c,n in yb.items() if n>=MIN_N}
tr=[(r["text"],r["register"]) for r in sv if r["register"] in keep]
recs=json.load(open(CMP,encoding="utf-8"))

st=SentenceTransformer(MODEL)
Xtr=st.encode(["passage: "+t[:1200] for t,_ in tr],batch_size=32,normalize_embeddings=True,show_progress_bar=False)
clf=LogisticRegression(max_iter=4000,class_weight="balanced",C=10.0).fit(Xtr,[y for _,y in tr])
Xin=st.encode(["passage: "+r["text"][:1200] for r in recs],batch_size=32,normalize_embeddings=True,show_progress_bar=False)
e5=clf.predict(Xin)
for r,p in zip(recs,e5): r["e5"]=p

def norm(x): return {"opinia":"opinie"}.get(x,x)
rows=[(norm(r["human"]),r["opus"],r["e5"]) for r in recs]
info=[r for r in rows if r[0]=="info"]
comp=[r for r in rows if r[0]!="info"]   # gdzie porownanie sprawiedliwe (klasyfikator zna klase)

def acc(pairs,idx): return sum(1 for r in pairs if r[idx]==r[0])/len(pairs) if pairs else 0
print(f"=== WALIDACJA na HUMAN-gold (n=30; {len(comp)} porownywalne, {len(info)} 'info'=luka taksonomii) ===")
print(f"opus vs human (comp): {acc(comp,1):.2f}   ({sum(1 for r in comp if r[1]==r[0])}/{len(comp)})")
print(f"e5   vs human (comp): {acc(comp,2):.2f}   ({sum(1 for r in comp if r[2]==r[0])}/{len(comp)})")
print(f"e5   vs auto-labeler  (all) : {sum(1 for r in rows if r[2]==r[1])/len(rows):.2f}")
print("\n--- per-doc (human | opus | e5) ---")
for i,(h,o,e) in enumerate(rows,1):
    flag="" if (o==h and e==h) else ("  <e5≠h" if e!=h else "")+("  <opus≠h" if o!=h else "")
    print(f"{i:2} {h:16} | {o:16} | {e:16}{flag}")
print("\n--- 'info' (klasyfikator nie zna tej klasy - jak zmapowal): ---")
for h,o,e in info: print(f"   human=info -> opus={o}, e5={e}")
