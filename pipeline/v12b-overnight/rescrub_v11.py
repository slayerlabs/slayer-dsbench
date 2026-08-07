# -*- coding: utf-8 -*-
"""Re-scrub existing 15 shards z v11 (catches v10-missed phones — wciaz raw w tekscie, NO re-fetch)
+ auto-clean-mangle. Uzycie: python rescrub_v11.py <parquet>...
"""
import sys, re
sys.path.insert(0, r"C:/tmp")
import phone_scrub_labelwindow as M
from auto_clean_mangle import clean as mangle_clean
import pyarrow as pa, pyarrow.parquet as pq

def scrub_fix(x, cap=8):
    tot = 0
    for _ in range(cap):
        x, n = M.scrub_phones_labelwindow(x); tot += n
        if n == 0: break
    return x, tot

def run(paths):
    for fp in paths:
        t = pq.read_table(fp); cols = {c: t.column(c).to_pylist() for c in t.column_names}
        ns = nm = 0; new = []
        for x in cols["text"]:
            if not x:
                new.append(x); continue
            y, c = scrub_fix(x); ns += c
            y, m = mangle_clean(y); nm += m
            new.append(y)
        cols["text"] = new
        pq.write_table(pa.table(cols, schema=t.schema), fp, compression="zstd")
        print(f"{fp.split('/')[-1]}: v11-newscrub={ns} mangle-clean={nm}", flush=True)
    print("RESCRUB-DONE", flush=True)

if __name__ == "__main__":
    run(sys.argv[1:])
