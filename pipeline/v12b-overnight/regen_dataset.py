# -*- coding: utf-8 -*-
"""Regenerate shards CZYSTO (single-pass, all-fixes, decoupled od PR-merge-state).
Per shard: clean_hplt_v3(email/HPLT+NATID+[Telefon]phone+filtry) -> scratch polish(10-klas) -> post-PII(v6-phone [Telefon]).
Uzycie: python regen_dataset.py <tier_shard>...   (np. 9_2 albo wszystkie 15)
"""
import sys, subprocess, re, glob
sys.path.insert(0, r"C:/tmp")
from phone_scrub_labelwindow import scrub_phones_labelwindow
import pyarrow as pa, pyarrow.parquet as pq

PY = r"C:/tmp/dml-venv/Scripts/python.exe"
CLEAN = r"C:/tmp/dsbench-monter/pipeline/clean_hplt_v3.py"
POLISH = r"C:/tmp/polish_dataset.py"
OUT = r"C:/Projekty/Slayer/datasets/polish-dynaword-expansion"
URL = "https://data.hplt-project.org/three/sorted/pol_Latn/{b}.jsonl.zst"
# widened-NATID (Mierniczy pii-patch, symetria check<->scrub)
NATID = re.compile(r"(?i)((?:PESEL|NIP|REGON|dow[o\u00f3]d\s+osobist\w*)[\s:.\-]*(?:(?:nr|numer|to|wynosi|jest)\.?[\s:.\-]*){0,2})(\d[\d\s\-]{7,13}\d)")


def scrub_fix(x, cap=8):
    """Bounded-fixpoint v6: scrubuje list-tail phones (za 55-oknem, wjezdzaja po [Telefon]-shrink).
    CONVERGENTNY (pass3=0 na 9_2) + guard-protected phone-only (NIE divergentny-cascade). cap=safety."""
    tot=0
    for _ in range(cap):
        x,n=scrub_phones_labelwindow(x); tot+=n
        if n==0: break
    return x,tot

def run(bins):
    for b in bins:
        src=f"european_hplt_v3_pl_{b}"; tier=b.split("_")[0]; fp=f"{OUT}/{src}.parquet"
        print(f"=== {b} KROK1 clean ===",flush=True)
        r=subprocess.run([PY,CLEAN,"--in",URL.format(b=b),"--out-dir",OUT,"--source",src,"--bin-label",f"WDS={tier}","--max-records","100000","--max-per-domain","50"],capture_output=True,text=True)
        if r.returncode: print(f"!!! {b} CLEAN FAIL: {r.stderr[-300:]}",flush=True); continue
        print(f"=== {b} KROK2 polish ===",flush=True)
        subprocess.run([PY,POLISH,"--parquet",fp,"--apply"],capture_output=True,text=True)
        print(f"=== {b} KROK3 post-PII (v6-phone [Telefon]; NATID via KROK1) ===",flush=True)
        t=pq.read_table(fp); cols={c:t.column(c).to_pylist() for c in t.column_names}
        np_=0; new=[]
        for x in cols["text"]:
            x,c2=scrub_fix(x); np_+=c2; new.append(x)
        cols["text"]=new; pq.write_table(pa.table(cols,schema=t.schema),fp,compression="zstd")
        pr=sum(scrub_phones_labelwindow(x)[1] for x in new)   # TRUE residual = v6-idempotency (check==scrub, FCD-R4)
        nr=sum(len(NATID.findall(x)) for x in new)            # widened-NATID CHECK-only (>= KROK1-narrow scrub)
        tk=sum(cols["token_count"])
        print(f"{b} DONE: docs={len(new)} tok={tk/1e6:.1f}M | phone-scrub={np_} | RESID phone(idem)={pr} natid(wide-chk)={nr}",flush=True)
    print("REGEN-DONE",flush=True)

if __name__=="__main__": run(sys.argv[1:])
