#!/usr/bin/env python3
"""Deterministyczny garbage-detektor (reguly z human-gold Arka, batch 01-03). R5 as_kuracja-hplt.
action: quarantine (caly doc smiec) | strip (boilerplate do wyciecia, doc zostaje).
Batch-03 (Arek 15 werdyktow): 'teaser_listing >=3' OBALONE jako kill -> to STRIP (8/15 wytnij, 4/15 zostaw,
2/15 usun); licznik nie rozroznia. Kill tylko wysokoprecyzyjne sygnatury spamu.
Uzycie: python garbage_rules.py [N]"""
import sys, re, json, pyarrow.parquet as pq
from collections import Counter

RX = {
  "dating_profile": re.compile(r"Imię:\s*\w+.{0,120}?Wiek:\s*\d+.{0,200}?(Szukam:|Skontaktuj się ze mną|Numer tel)", re.I | re.S),
  "oldman_synonym_spam": re.compile(r"Santiago\s+owo|nie złowił żadnej ryby|siedemdziesięciu czterech dni", re.I),
  "seo_catalog": re.compile(r"PageRank:.{0,200}?(Kliknięć|CTR)\s*:|Ocena moderatora:|Wyróżnij ten wpis", re.I | re.S),
  "job_listing_boiler": re.compile(r"Czy chcesz otrzymywać podobne oferty pracy|prześlij swoje CV|Utwórz powiadomienie", re.I),
  "site_counter": re.compile(r"Odwiedziło nas:\s*[\d\s]+osób", re.I),
  "forum_online_nav": re.compile(r"Użytkownicy przeglądający to forum[^.]*", re.I),
}
READ_MORE = re.compile(r"czytaj\s+więcej|czytaj\s+dalej", re.I)

def detect(text):
    t = text or ""
    q, s = [], []
    for name in ("dating_profile", "oldman_synonym_spam", "seo_catalog", "job_listing_boiler"):
        if RX[name].search(t): q.append(name)
    rm = len(READ_MORE.findall(t))            # batch-03: >=1 -> STRIP bloki (nie kill), licznik nie rozroznia
    if rm >= 1: s.append(f"czytaj-wiecej-bloki(×{rm})")
    for name in ("site_counter", "forum_online_nav"):
        if RX[name].search(t): s.append(name)
    return q, s

def scan(path, N):
    pf = pq.ParquetFile(path); seen=0; nq=0; qc=Counter(); sc=Counter(); ex={}
    for rg in range(pf.num_row_groups):
        if seen>=N: break
        for t in pf.read_row_group(rg, columns=["text"]).column("text").to_pylist():
            if seen>=N: break
            seen+=1; q,s=detect(t)
            if q:
                nq+=1
                for r in q:
                    key=r.split("(")[0]; qc[key]+=1
                    if key not in ex: ex[key]=(t or "")[:110]
            for r in s: sc[r.split("(")[0]]+=1
    return seen,nq,qc,sc,ex

if __name__=="__main__":
    N=int(sys.argv[1]) if len(sys.argv)>1 else 200000
    seen,nq,qc,sc,ex=scan("/mnt/c/Projekty/datasets/build/web/web-slice-0.parquet", N)
    print(f"=== GARBAGE-RULES v3 (teaser->strip, batch-03) skan N={seen} ===")
    print(f"QUARANTINE (kill): {nq} ({100*nq/seen:.2f}%)")
    for r,c in qc.most_common(): print(f"  [KILL] {r:22} {c:6} ({100*c/seen:.2f}%)")
    print("STRIP (zostaw doc, wytnij fragment):")
    for r,c in sc.most_common(): print(f"  [STRIP] {r:20} {c:6} ({100*c/seen:.2f}%)")
    json.dump({"N":seen,"quarantine_pct":round(100*nq/seen,3),"per_rule_kill":dict(qc),"per_rule_strip":dict(sc)},
              open("/mnt/c/Projekty/Slayer/slayer-dsbench/eval_sets/garbage-rules-scan-v3.json","w",encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("zapis -> eval_sets/garbage-rules-scan-v3.json")
