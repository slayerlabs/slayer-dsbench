#!/usr/bin/env python3
"""Lekki PII-check (sample) na zbudowanym 8x3b: liczy surowe e-maile/telefony/PESEL POZA placeholderami
zrodla ([PII],[Telefon]). Nie blokuje (karta: audyt PII po stronie odbiorcy) - raportuje skale."""
import glob, re, json
import pyarrow.parquet as pq

DS = "/mnt/c/Projekty/datasets/slayer-pl-8x3b"
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE = re.compile(r"(?<!\d)(?:\+48\s?)?(?:\d[ -]?){9}(?!\d)")
PESEL = re.compile(r"(?<!\d)\d{11}(?!\d)")
N_PER = 20000

def scan(path):
    n = e = ph = pe = 0
    for b in pq.ParquetFile(path).iter_batches(batch_size=5000, columns=["text"]):
        for t in b.column("text").to_pylist():
            if n >= N_PER: break
            n += 1; t = t or ""
            e += len(EMAIL.findall(t)); ph += len(PHONE.findall(t)); pe += len(PESEL.findall(t))
        if n >= N_PER: break
    return {"probka": n, "email": e, "telefon": ph, "pesel_like": pe}

if __name__ == "__main__":
    out = {}
    for f in sorted(glob.glob(f"{DS}/shared/*.parquet")) + sorted(glob.glob(f"{DS}/pack-*/web.parquet")):
        k = f.replace(DS + "/", "")
        out[k] = scan(f)
        print(k, out[k])
    json.dump(out, open(f"{DS}/pii-check.json", "w"), ensure_ascii=False, indent=2)
    tot = {kk: sum(v[kk] for v in out.values()) for kk in ("email", "telefon", "pesel_like")}
    print("SUMA (na probkach):", tot)
