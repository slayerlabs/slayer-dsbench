#!/usr/bin/env python3
"""Walidacja glimmera jako labelera rejestrow (baseline-first dla labelera, R4/as_kuracja-hplt).
meta/muse-glimmer = model BAZOWY -> /v1/completions few-shot (NIE chat). Mierzy zgodnosc glimmer-vs-opus
na silver-v1 zanim zaufamy mu na bulk train-set. Uzycie: python glimmer_label.py [n]"""
import sys, json, urllib.request, random
from collections import Counter, defaultdict

PATH = "/mnt/c/Projekty/Slayer/slayer-dsbench/eval_sets/hplt-register-silver-v1.jsonl"
URL = "http://127.0.0.1:1234/v1/completions"
REG = ["news","howto","qa","dialog","literacki","nauka","encyklopedyczny","opinie","legal","web-inne"]
N = int(sys.argv[1]) if len(sys.argv) > 1 else 120

FEWSHOT = (
"Zadanie: przypisz polskiemu fragmentowi web DOKLADNIE JEDEN rejestr z listy: "
+ ", ".join(REG) + ".\n\n"
"Fragment: Prezydent podpisal dzis ustawe budzetowa na przyszly rok.\nrejestr=news\n\n"
"Fragment: Wymieszaj make z jajkami, dodaj mleko i smaz na zloty kolor.\nrejestr=howto\n\n"
"Fragment: Jak zresetowac haslo? Wejdz w ustawienia konta i kliknij Zmien haslo.\nrejestr=qa\n\n"
"Fragment: - Idziesz jutro na spotkanie? - Pewnie, o ktorej sie umawiamy?\nrejestr=dialog\n\n"
"Fragment: Ksiezyc wznosil sie powoli nad cichym jeziorem, mgla snula sie nisko.\nrejestr=literacki\n\n"
"Fragment: Fotosynteza przeksztalca dwutlenek wegla i wode w glukoze przy udziale swiatla.\nrejestr=nauka\n\n"
"Fragment: Warszawa - stolica Polski, polozona nad Wisla, najwieksze miasto kraju.\nrejestr=encyklopedyczny\n\n"
"Fragment: Film byl przecietny, gra aktorska ratuje calosc, scenariusz slaby.\nrejestr=opinie\n\n"
"Fragment: Art. 5. Przepisy ustawy stosuje sie do umow zawartych po dniu wejscia w zycie.\nrejestr=legal\n\n"
"Fragment: Sprzedam mieszkanie 3 pokoje, 54 m2, centrum, kontakt telefoniczny.\nrejestr=web-inne\n\n"
)

def label(text):
    body = json.dumps({"model":"meta/muse-glimmer","prompt":FEWSHOT+f"Fragment: {text[:500]}\nrejestr=",
                       "max_tokens":5,"temperature":0,"stop":["\n"]}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type":"application/json"})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=30).read())
        out = (r["choices"][0].get("text") or "").strip().lower()
        for rg in REG:
            if rg in out: return rg
        return out.split()[0] if out.split() else "?"
    except Exception as e:
        return f"ERR:{type(e).__name__}"

rows = [json.loads(l) for l in open(PATH, encoding="utf-8") if l.strip()]
random.seed(11); random.shuffle(rows)
sample = rows[:N]
agree = 0; conf = defaultdict(Counter); n_ok = 0
pairs = []
for i, r in enumerate(sample):
    g = label(r["text"]); o = r["register"]
    pairs.append((o, g))
    if g.startswith("ERR"): continue
    n_ok += 1
    conf[o][g] += 1
    if g == o: agree += 1
    if (i+1) % 30 == 0: print(f"  ...{i+1}/{N}", flush=True)

print(f"\n=== GLIMMER vs OPUS (n_ok={n_ok}/{N}) ===")
print(f"zgodnosc (accuracy) = {agree/n_ok:.3f}" if n_ok else "brak")
# per-rejestr recall glimmera wzgl. opus-labela
print("\nopus_rejestr -> jak glimmer tagowal (n):")
for o in REG:
    if conf[o]:
        tot = sum(conf[o].values()); match = conf[o][o]
        top = ", ".join(f"{k}={v}" for k,v in conf[o].most_common(3))
        print(f"  {o:16} match={match}/{tot} ({100*match/tot:.0f}%)  [{top}]")
errs = sum(1 for _,g in pairs if g.startswith("ERR"))
if errs: print(f"\nbledy HTTP: {errs}")
json.dump({"n":N,"n_ok":n_ok,"agreement":round(agree/max(n_ok,1),4),
           "confusion":{o:dict(c) for o,c in conf.items()}},
          open("/mnt/c/Projekty/Slayer/slayer-dsbench/eval_sets/glimmer-vs-opus.json","w",encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("\nzapis -> eval_sets/glimmer-vs-opus.json")
