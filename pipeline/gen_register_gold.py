#!/usr/bin/env python3
"""Batch register-gold: losowe CZYSTE (nie-kwarantanna) doce -> pytanie o REJESTR (human-gold do walidacji
klasyfikatora e5 na prawdzie, nie silver; rozstrzyga AT1.1). Pelny tekst do 1500 zn.
Uzycie: python gen_register_gold.py <numer> [N]"""
import sys, json, random, pyarrow.parquet as pq
sys.path.insert(0, "/mnt/c/Projekty/Slayer/slayer-dsbench/pipeline")
from garbage_rules import detect

BATCH = sys.argv[1] if len(sys.argv) > 1 else "04"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 30
SLICE = "/mnt/c/Projekty/datasets/build/web/web-slice-0.parquet"
random.seed(int(BATCH) + 500)

pf = pq.ParquetFile(SLICE)
keepers = []
for rg in range(pf.num_row_groups):
    if len(keepers) >= N*6: break
    t = pf.read_row_group(rg, columns=["text","document_id"])
    for txt, did in zip(t.column("text").to_pylist(), t.column("document_id").to_pylist()):
        q, s = detect(txt or "")
        if not q and len(txt or "") > 300:          # czyste (nie-kill), sensownej dlugosci
            keepers.append((did, txt))
random.shuffle(keepers)
picked = keepers[:N]

md = [f"# Register-gold partia {BATCH} — jaki REJESTR?",
      "", f"{len(picked)} czystych fragmentów (bez śmieci). **Dla każdego wpisz `rejestr:` JEDNO:**",
      "",
      "| id | co to |",
      "|---|---|",
      "| `news` | wiadomości, dziennikarstwo, relacje |",
      "| `howto` | poradnik, instrukcja, przepis, krok-po-kroku |",
      "| `qa` | pytania-odpowiedzi, FAQ, forum Q&A |",
      "| `dialog` | rozmowa, komentarze konwersacyjne |",
      "| `literacki` | proza, poezja, narracja, beletrystyka |",
      "| `nauka` | naukowe, popularnonaukowe, techniczno-wyjaśniające |",
      "| `encyklopedyczny` | hasła, definicje, reference |",
      "| `opinie` | recenzje, publicystyka oceniająca |",
      "| `legal` | prawne, urzędowe, regulaminy, akty |",
      "| `web-inne` | sensowny web nie pasujący wyżej |",
      "",
      "- jeśli mimo wszystko to śmieć — wpisz `usuń`",
      "- po rejestrze dopisz cokolwiek (wątpliwość, druga możliwość)",
      ""]
recs = []
for i, (did, txt) in enumerate(picked, 1):
    md.append(f"## {i}.")
    md.append(f"> {(txt or '')[:1500]}")
    md.append("rejestr: ______")
    md.append("")
    recs.append({"id": did, "text": txt, "rejestr": ""})
mdp = f"/mnt/c/Projekty/private/labvault-local/01_ArekSłota/28_08_Klasyfikator-Rejestrow-HPLT/45-Eksperymenty/register-gold-partia-{BATCH}.md"
jlp = f"/mnt/c/Projekty/Slayer/slayer-dsbench/eval_sets/register-gold-partia-{BATCH}.jsonl"
open(mdp,"w",encoding="utf-8").write("\n".join(md))
open(jlp,"w",encoding="utf-8").write("\n".join(json.dumps(r,ensure_ascii=False) for r in recs))
print(f"register-gold {BATCH}: {len(picked)} czystych doców")
print(f"  MD -> {mdp}")
