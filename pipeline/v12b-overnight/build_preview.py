# -*- coding: utf-8 -*-
"""Build wglad-package dla Arka: PREVIEW-korpus.parquet (concat 15 distinct) + SAMPLE-korpus.txt + .stats.json.
Uzycie: python build_preview.py   (po regenerate)
"""
import glob, json, random, re
import pyarrow as pa, pyarrow.parquet as pq
sys_dir=r"C:/Projekty/Slayer/datasets/polish-dynaword-expansion"
import sys; sys.path.insert(0,r"C:/tmp")
from phone_scrub_labelwindow import scrub_phones_labelwindow, PHONE_LABEL, PHONE_NUM, WINDOW, _DATE, _KRS, _ISBN
DISTINCT=["5_1","5_2","6_1","6_2","7_1","7_2","7_3","7_4","8_1","8_2","8_3","8_4","9_2","9_3","9_4"]

def presid(t):
    n=0
    for m in PHONE_LABEL.finditer(t):
        for nm in PHONE_NUM.finditer(t[m.end():m.end()+WINDOW]):
            d=re.sub(r"\D","",nm.group())
            if 9<=len(d)<=11 and not(_KRS.search(nm.group()) or _DATE.search(nm.group()) or _ISBN.search(nm.group())) and set(d)!={"0"}: n+=1
    return n

tabs=[]; per={}; tot_tok=0; tot_doc=0; dom={}
for b in DISTINCT:
    fp=f"{sys_dir}/european_hplt_v3_pl_{b}.parquet"
    try: t=pq.read_table(fp)
    except Exception as e: print(f"skip {b}: {e}"); continue
    tabs.append(t); n=t.num_rows; tk=sum(t.column("token_count").to_pylist())
    per[b]={"docs":n,"tok_M":round(tk/1e6,1)}; tot_doc+=n; tot_tok+=tk
    if "domain" in t.column_names:
        for d in t.column("domain").to_pylist(): dom[d]=dom.get(d,0)+1

big=pa.concat_tables(tabs, promote_options="default")
pq.write_table(big, f"{sys_dir}/PREVIEW-korpus.parquet", compression="zstd")

# SAMPLE 40 losowych docs
texts=big.column("text").to_pylist(); random.seed(42)
samp=random.sample(range(len(texts)), min(40,len(texts)))
with open(f"{sys_dir}/SAMPLE-korpus.txt","w",encoding="utf-8") as f:
    for i in samp: f.write(f"===== doc[{i}] =====\n{texts[i][:1500]}\n\n")

# residual = v10-idempotency (2nd-pass scrub = TRUE residual, FCD-R4 check==scrub); + mangle-scan
import re as _re
presid_tot=sum(scrub_phones_labelwindow(x)[1] for x in texts)
mangle_tot=sum(len(_re.findall(r'\[Telefon\][-\d]',x)) for x in texts)
stats={"distinct_shards":len([b for b in DISTINCT if b in per]),"total_docs":tot_doc,"total_tokens_V32000_est":tot_tok,
       "total_tokens_M":round(tot_tok/1e6,1),"per_shard":per,"top_domains":dict(sorted(dom.items(),key=lambda x:-x[1])[:15]),
       "phone_residual_idem_v10":presid_tot,"mangle_artefacts":mangle_tot,"note":"v10 phone-scrub (cluster-guard+leading-0+kom)->[Telefon]; email/NATID->[PII]; 10-klas-polish; auto-mangle-cleaned; bin9=9_2-dup dropped; residual=v10-idempotency; authoritative-verify=Wartownik-deep+Latarnik-broad"}
json.dump(stats, open(f"{sys_dir}/PREVIEW-korpus.stats.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps(stats,ensure_ascii=False,indent=2))
