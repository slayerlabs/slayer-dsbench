# -*- coding: utf-8 -*-
"""auto-clean-pass (Wartownik idea): trim mangle-artefakty [Telefon]<przylegla-cyfra/myslnik><cluster>.
KONSERWATYWNIE: tylko DIRECTLY-adjacent (bez spacji) = mangle-remnant; space-separated (legit '[Telefon] 24h') NIEtkniete.
Uzycie: python auto_clean_mangle.py <parquet>...  (in-place, po batchu przed preview)
"""
import sys, re
import pyarrow as pa, pyarrow.parquet as pq

# mangle-remnant: cyfry bezposrednio przylegle do [Telefon] (trailing LUB leading) -> trim
MANGLE_T = re.compile(r"\[Telefon\][-\d][\d \-]*")            # trailing: [Telefon]0 0000 / [Telefon]4 / [Telefon]-63
MANGLE_L = re.compile(r"\d[\d \-]*[\d\-]\[Telefon\]")         # leading: 107[Telefon] / (0[Telefon] (directly-adjacent, space-sep legit NIEtkniete)

def clean(text):
    text, a = MANGLE_T.subn("[Telefon]", text)
    text, b = MANGLE_L.subn("[Telefon]", text)
    return text, a + b

def run(paths):
    for fp in paths:
        t = pq.read_table(fp); cols = {c: t.column(c).to_pylist() for c in t.column_names}
        n = 0; new = []
        for x in cols["text"]:
            y, c = clean(x); n += c; new.append(y)
        cols["text"] = new
        pq.write_table(pa.table(cols, schema=t.schema), fp, compression="zstd")
        print(f"{fp.split('/')[-1]}: mangle-trimmed={n}", flush=True)

if __name__ == "__main__":
    run(sys.argv[1:])
