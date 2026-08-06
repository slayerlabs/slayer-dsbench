# -*- coding: utf-8 -*-
"""run_pipeline.py — MODULARNY, ROZSZERZALNY pipeline HPLT->dataset (jeden bin, jedna komenda).
Composuje niezalezne, reuzywalne kroki (kazdy = osobny modul/skrypt):
  KROK 1  clean_hplt_v3.py   : fetch(raw HPLT bin) -> filtry(lang/MT/register/len/boilerplate/adult/mojibake/domain)
                               + PII-scrub(email HPLT-spans + phone-regex) + residual-gate(stats)
  KROK 2  polish_dataset.py  : block-frame_merge + leading-nav-list + Strona-strip + '?'-artefakt-strip
  KROK 3  (opcja) near_dup_vs_dynaword.py : dedup vs istniejacy korpus

Rozszerzalnosc: nowy bin = --bin 8_1|7_1|... ; nowe zrodlo = --url ; nowy krok = dopisz do STEPS.
Modularnosc: kazdy krok wolany jako osobny proces (mozna uzyc/testowac samodzielnie); wspolny kontrakt = parquet(kanoniczna schema).
"""
import argparse, subprocess, sys, time
from pathlib import Path
PY=sys.executable
SRC=Path(__file__).resolve().parent  # self-contained: wszystkie moduly w tym samym src/

def run(cmd, label):
    print(f"\n>>> {label}\n$ {' '.join(cmd)}", flush=True)
    t=time.time(); r=subprocess.run(cmd, capture_output=True, text=True)
    tail="\n".join((r.stdout or "").splitlines()[-12:])
    print(tail, flush=True)
    if r.returncode!=0:
        print(f"!!! KROK FAIL ({label}) rc={r.returncode}\n{(r.stderr or '')[-500:]}", flush=True); sys.exit(1)
    print(f"[{time.time()-t:.0f}s] OK {label}", flush=True); return r.stdout

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--bin", required=True, help="np. 9_1 (WDS-bin_shard)")
    ap.add_argument("--out-dir", default=r"C:\Projekty\Slayer\datasets\polish-dynaword-expansion")
    ap.add_argument("--max-records", type=int, default=15000)
    ap.add_argument("--max-per-domain", type=int, default=250, help="diversity-knob: max docow/domene (nizej=rozniorodniej)")
    ap.add_argument("--url", default="https://data.hplt-project.org/three/sorted/pol_Latn/{bin}.jsonl.zst")
    ap.add_argument("--dedup-ref", default="", help="glob parquetow ref do near_dup (opcja); pusty=skip")
    ap.add_argument("--source", default="", help="override nazwy source/pliku (default bin{tier}); uzyj dla wielu shardow tego samego tieru bez clobber, np. european_hplt_v3_pl_8_2")
    a=ap.parse_args()
    tier=a.bin.split("_")[0]; src=a.source or f"european_hplt_v3_pl_bin{tier}"
    url=a.url.format(bin=a.bin); outd=Path(a.out_dir); parq=outd/f"{src}.parquet"
    t0=time.time()
    # KROK 1: clean + PII-scrub + residual-gate
    run([PY, str(Path(SRC)/"clean_hplt_v3.py"), "--in", url, "--out-dir", str(outd),
         "--source", src, "--bin-label", f"WDS={tier}", "--max-records", str(a.max_records),
         "--max-per-domain", str(a.max_per_domain)], "KROK1 clean_hplt_v3+PII")
    # KROK 2: polish (4 fixy)
    run([PY, str(SRC/"polish_dataset.py"), "--parquet", str(parq), "--apply"], "KROK2 polish_dataset")
    # KROK 3: dedup (opcja)
    if a.dedup_ref:
        run([PY, str(SRC/"near_dup_vs_dynaword.py"), "--ref", a.dedup_ref, "--cand", str(parq),
             "--limit-ref", "40000"], "KROK3 near_dup_vs_dynaword")
    print(f"\n=== PIPELINE DONE bin {a.bin} -> {parq} ({time.time()-t0:.0f}s) ===", flush=True)

if __name__=="__main__": main()
