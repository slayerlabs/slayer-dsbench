---
type: ewaluacja
id: EVAL
title: "Stan projektu — żywy audyt SpeakLeash"
status: zywy-dokument
author: Arkadiusz Słota
date: 2026-07-10
created_at: 2026-07-10
---

# Stan projektu — ewaluacja (żywy audyt SpeakLeash)
> Żadnej tezy bez dowodu. Co się NAPRAWDĘ dzieje. Aktualizuj po każdym istotnym kroku.

## ✅ Działa (z dowodem / liczbą)
| Co | Dowód (liczba / źródło / output) |
|---|---|
| Testy silnika bez regresji | `python tests/test_dsbench.py` → 27/27 PASS |
| `datasets/speakleash/` audytowany w CI (fixture) | `dsbench audit --card datasets/speakleash/card.yaml` → PASS, 0 błędów, 2 ostrzeżenia |
| Per-source summary (fixture) | INFO „licencje per źródło (6 dok.)": 6 źródeł, każde UNKNOWN |
| Żywy audyt realnego shardu _0006 | 3 doki `web_synt_0012` (dekompresja `zstandard`) → PASS, PII czyste |
| Bramka FAIL-uje na realnym zatruciu | slice 2211 dok. z _0001 (6 źródeł) → FAIL: **18 PESEL** wykryte (+ 35 e-mail, 130 tel.) |
| Dekompresja `.zst` (brak `zstd` CLI) | `python zstandard` → 16972 B / 3 rek. (_0006) w ok. 0,2 s |

## ❌ Nie działa / otwarte
| Co | Co wyszło / czego brak |
|---|---|
| Twardy FAIL na NC/ND na REALU | Niesprawdzony — 76 źródeł to UNKNOWN (WARN), brak realnych SPDX (D1, `maggi-c2i`) |
| Port bramki per-źródło Bartka | Kod niedostępny lokalnie (polish-dynaword = same parquet) (D2, `maggi-ju0`) |
| PR na `slayerlabs/slayer-dsbench` | `gh` niezalogowany → link compare + body w `%TEMP%` (do otwarcia ręcznie) |
| Dataset Piotra | Osobna nitka `maggi-dvp` — poza zakresem C1 |

## 🔄 Co się zmieniło (2026-07-10)
- Commit `a0be576` na `feat/license-per-source-gate`: `datasets/speakleash/{card.yaml,sample.jsonl}` — wpięcie do CI.
- Karta bez `records`/`sha256` (D4) — naprawia fałszywy FAIL na realnych podzbiorach shardów.
- bd: pamięć `slayer-dsbench-live-audit` + issue `maggi-ju0`, `maggi-c2i` (discovered-from `maggi-vct`).

## Pętla empiryczna (TYLKO twierdzenia z metryką)
> Najpierw baseline / próg z góry, potem wynik. Higiena: werdykt CI zależy tylko od gwarantowanego fixture (D3).

| Problem | Metryka (n) | Baseline | Próg (z góry) | Metoda | Wynik | Werdykt |
|---|---|---|---|---|---|---|
| Czy bramka przepuszcza czyste? | verdict (n=6, fixture) | naiwna karta = PASS zawsze | PASS gdy 0 restr. + 0 PII | manifest + per-rekord + PII | PASS | zgodne |
| Czy bramka łapie realne PII? | PESEL (n=2211, real) | naiwna karta = PASS | FAIL gdy min. 1 PESEL | check `pii` na treści | FAIL, 18 PESEL | zgodne |
| Czy realny _0006 = PASS? | verdict (n=3, real) | — | PASS gdy 0 PII | pełny audyt | PASS | zgodne |

## Czy tezy/syntezy się bronią?
- **T1**: ⚠️ częściowo — grupowanie per-źródło + PASS/summary potwierdzone; twardy FAIL na NC/ND niesprawdzony (brak SPDX).
- **S1**: ✅ potwierdzona w 2 z 3 warunków (PASS-gdy-czyste, FAIL-gdy-PII). Warunek 3 (FAIL-gdy-NC/ND) otwarty do D1.
- **AT1**: N3 (PII to osobny wektor) **potwierdzona empirycznie** (18 PESEL). N1/N2 adresowane przez D1/D2, nie obalone.

## ➡️ Następne kroki
1. Otworzyć PR (link compare + body gotowe w `%TEMP%/dsbench_pr_body.md`).
2. Pozyskać mapę SPDX od Bartka → wpisać do `sources.yaml` → domknąć warunek obalenia S1 (`maggi-c2i`).
3. Pozyskać kod bramki Bartka → port do silnika, apple-to-apple (`maggi-ju0`).
4. Ruszyć nitkę datasetu Piotra (`maggi-dvp`).
