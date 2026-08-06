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

## Relacja z `dsbench/checks`
Ten sam **policy** higieny po obu stronach (spójne, nie dwie konwencje):
- national-ID **keyword-adjacent** (PESEL/NIP/REGON/dowód) — `clean_hplt_v3` **usuwa**, `checks/pii.py` **wykrywa** (checksum-PESEL + label; naiwne `\d{11}` dawało 95 FP na czystym korpusie).
- near-dup **MinHash/LSH** — `near_dup_vs_dynaword` odsiewa cross-source, `checks/neardup.py` wykrywa w próbce (fuzzy, uzupełnia exact `dedup`).

## Zależności
Cięższe niż silnik dsbench (`pyyaml`+`pyarrow`): `clean_hplt_v3` używa `tiktoken` (token-count) + `pyarrow`.
Producent jest opcjonalny — instaluj gdy budujesz dataset, nie do samego audytu.

## Metoda
baseline-first · mierz-nie-zakładaj · reuse-nie-rebuild · każdy fix FP-safe + zmierzony z bajtów (0-na-czystej-prozie przed gate).
