# pipeline — producent czystych datasetów (HPLT → dynaword-schema)

Druga strona bramki `dsbench`: **`dsbench` audytuje, `pipeline` czyści.** Bierze surowy shard HPLT
i produkuje parquet (schema dynaword) który **przechodzi bramkę** (`dsbench audit`) — PII 0, boilerplate
zdjęty, near-dup odsiany, licencja per-źródło.

## Moduły
| moduł | rola |
|---|---|
| `clean_hplt_v3.py` | fetch raw HPLT bin → filtry (lang≥0.80 / MT<0.20 / register-whitelist / len 400–120k / boilerplate / adult / mojibake / domain-cap) → **PII-scrub** (HPLT-spany + phone-regex + **national-ID PESEL/NIP/REGON** keyword-adjacent) → **residual-gate** (re-scan OUTPUT, PASS/FAIL) |
| `polish_dataset.py` | post-process struktury (FP-safe): block-frame_merge · leading-nav-list · Strona-header · intra-word `?` (diacritic-loss) · leading bare-dash · **U+FFFD** (decode-junk) |
| `near_dup_vs_dynaword.py` | cross-source near-dedup MinHash-128 + LSH — net-new vs istniejący korpus |
| `run_pipeline.py` | driver: jedna komenda composuje moduły (`--bin`/`--source`/`--max-per-domain`/`--dedup-ref`) |

## Użycie
```bash
python pipeline/run_pipeline.py --bin 8_2 --source european_hplt_v3_pl_8_2 --max-per-domain 50
dsbench audit --card datasets/<name>/card.yaml   # bramka potwierdza higienę wyjścia
```

## slayer-pl-8x3b i klasyfikator rejestrów
Skrypty, którymi zbudowano i sprawdzono [SlayerLab/slayer-pl-8x3b](https://huggingface.co/datasets/SlayerLab/slayer-pl-8x3b):

| moduł | rola |
|---|---|
| `garbage_rules.py`, `tag_web.py`, `e5_gpu.py` | reguły śmieci (usuń / wytnij fragment) i tagowanie rejestru warstwy web (e5 + regresja logistyczna z `eval_sets/logreg_coef.npz`) |
| `recover_literacki.py` | odbudowa rejestru literackiego z polish-dynaword (dedup dokładny, dekontaminacja 8-gramami) |
| `assemble.py`, `finalize.py` | złożenie wspólnego rdzenia i 8 paczek web, manifesty z sha256, tokenami i rozkładem rejestrów, `dataset.json` |
| `pii_check.py` | **raport** z próbki (surowe e-maile, telefony, ciągi 11-cyfrowe poza placeholderami); nie blokuje, to nie bramka PII |
| `push.py` | wysyłka na HF |
| `register_baseline.py`, `register_embed*.py`, `register_calibrate.py`, `train_logreg.py`, `register_tag_pilot.py` | klasyfikator rejestrów: baseline TF-IDF, e5 + regresja logistyczna, progi pewności, pilot na próbce web |
| `gen_register_gold.py`, `gen_review_batch.py`, `validate_human.py`, `glimmer_label.py` | partie do ręcznego etykietowania i walidacja klasyfikatora na etykietach ręcznych |

Ścieżki: pliki repo (`eval_sets/`, `datasets/`) liczone względem repo; dane spoza repo pod `DSBENCH_DATA` (katalog z `slayer-pl-8x3b/`, `build/`, `polish-dynaword/`; bez zmiennej skrypt kończy się komunikatem); arkusze `.md` do ręcznego przeglądu w `DSBENCH_NOTES` (domyślnie katalog bieżący). Zależności tych skryptów: `pyarrow`, `numpy`, `tiktoken`, `scikit-learn`, `transformers`/`sentence-transformers`, `huggingface_hub`.

## Relacja z `dsbench/checks`
Ten sam **policy** higieny po obu stronach (spójne, nie dwie konwencje):
- national-ID **keyword-adjacent** (PESEL/NIP/REGON/dowód) — `clean_hplt_v3` **usuwa**, `checks/pii.py` **wykrywa** (checksum-PESEL + label; naiwne `\d{11}` dawało 95 FP na czystym korpusie).
- near-dup **MinHash/LSH** — `near_dup_vs_dynaword` odsiewa cross-source, `checks/neardup.py` wykrywa w próbce (fuzzy, uzupełnia exact `dedup`).

## Zależności
Cięższe niż silnik dsbench (`pyyaml`+`pyarrow`): `clean_hplt_v3` używa `tiktoken` (token-count) + `pyarrow`.
Producent jest opcjonalny — instaluj gdy budujesz dataset, nie do samego audytu.

## Metoda
baseline-first · mierz-nie-zakładaj · reuse-nie-rebuild · każdy fix FP-safe + zmierzony z bajtów (0-na-czystej-prozie przed gate).
