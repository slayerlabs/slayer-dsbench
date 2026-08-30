#!/usr/bin/env python3
"""Generuje partie human-review (active-learning). Skala POLSKA: zostaw/wytnij/usuń. Nazwy regul po polsku.
Uzycie: python gen_review_batch.py <numer> [K_usun K_wytnij K_losowe]"""
import sys, json, random, pyarrow.parquet as pq
sys.path.insert(0, "/mnt/c/Projekty/Slayer/slayer-dsbench/pipeline")
from garbage_rules import detect

# angielskie klucze reguł -> polskie nazwy do wyświetlenia
PL = {
    "teaser_listing": "strona-zajawki", "seo_catalog": "katalog-spam",
    "dating_profile": "profil-randkowy", "oldman_synonym_spam": "tekst-mielony-spam",
    "job_listing_boiler": "oferta-pracy-szablon", "read_more_tail": "ogon-czytaj-więcej",
    "site_counter": "licznik-odwiedzin", "forum_online_nav": "nawigacja-forum",
}
def plname(r):  # r bywa "teaser_listing(read_more×5)" -> zachowaj licznik
    base = r.split("(")[0]; suf = r[len(base):]
    return PL.get(base, base) + suf

BATCH = sys.argv[1] if len(sys.argv) > 1 else "03"
KU, KW, KL = (int(x) for x in (sys.argv[2:5] or [15, 5, 10]))
SLICE = "/mnt/c/Projekty/datasets/build/web/web-slice-0.parquet"
random.seed(int(BATCH) + 100)

pf = pq.ParquetFile(SLICE)
usun, wytnij, losowe = [], [], []
for rg in range(pf.num_row_groups):
    if len(usun) >= KU*4 and len(wytnij) >= KW*4 and len(losowe) >= KL*4: break
    t = pf.read_row_group(rg, columns=["text","document_id"])
    for txt, did in zip(t.column("text").to_pylist(), t.column("document_id").to_pylist()):
        q, s = detect(txt or "")
        if q and len(usun) < KU*4: usun.append((did, txt, "podejrzenie USUŃ: " + ", ".join(plname(r) for r in q)))
        elif s and len(wytnij) < KW*4: wytnij.append((did, txt, "podejrzenie WYTNIJ: " + ", ".join(plname(r) for r in s)))
        elif not q and not s and len(losowe) < KL*4 and len(txt or "") > 200: losowe.append((did, txt, "losowy (bez reguły)"))
usun.sort(key=lambda x: 0 if "strona-zajawki" in x[2] else 1)
random.shuffle(wytnij); random.shuffle(losowe)
picked = usun[:KU] + wytnij[:KW] + losowe[:KL]; random.shuffle(picked)

md = [f"# Human-review partia {BATCH}",
      "", f"{len(picked)} fragmentów, pełny tekst. **Dla każdego wpisz `werdykt:` jedno słowo:**",
      "- **`zostaw`** — dobry dokument, bierzemy w całości (możesz dopisać rejestr)",
      "- **`wytnij`** — dobry, ale wytnij śmieciowy fragment (np. „czytaj więcej”, stopkę)",
      "- **`usuń`** — cały dokument to śmieć/listing/spam → kwarantanna",
      "- po słowie dopisz cokolwiek (nowy wzorzec śmieci = złoto)",
      "", "> Najważniejsze: sprawdź „podejrzenie USUŃ: strona-zajawki” (≥3× „czytaj więcej”) — czy to naprawdę strona-listing (`usuń`), czy realny artykuł z linkami (`zostaw`)? Twój werdykt promuje albo obala regułę.", ""]
recs = []
for i, (did, txt, flag) in enumerate(picked, 1):
    md.append(f"## {i}. [{flag}]")
    md.append(f"> {(txt or '')[:1500]}")
    md.append("werdykt: ______")
    md.append("")
    recs.append({"id": did, "podejrzenie": flag, "text": txt, "werdykt": ""})
mdp = f"/mnt/c/Projekty/private/labvault-local/01_ArekSłota/28_08_Klasyfikator-Rejestrow-HPLT/45-Eksperymenty/human-review-partia-{BATCH}.md"
jlp = f"/mnt/c/Projekty/Slayer/slayer-dsbench/eval_sets/human-review-partia-{BATCH}.jsonl"
open(mdp,"w",encoding="utf-8").write("\n".join(md))
open(jlp,"w",encoding="utf-8").write("\n".join(json.dumps(r,ensure_ascii=False) for r in recs))
nt = sum(1 for _,_,f in picked if "strona-zajawki" in f)
print(f"partia {BATCH}: {len(picked)} (strona-zajawki do walidacji: {nt})")
print(f"  MD -> {mdp}")
