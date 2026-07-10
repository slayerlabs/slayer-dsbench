---
type: decyzja
id: D4
title: "Karta speakleash bez `records` i `sha256` (integrity liczy total na --data)"
status: zaakceptowana
parents: ["C1"]
implements: ["S1"]
author: Arkadiusz Słota
date: 2026-07-10
created_at: 2026-07-10
data_decyzji: 2026-07-10
---

# D4 — Karta bez `records`/`sha256`

## Decyzja
`datasets/speakleash/card.yaml` NIE deklaruje `records` ani `sha256`.

## Rozważone alternatywy
- **`records: 6`** (liczba rekordów fixture): ODRZUCONE. Check `integrity` liczy total TYLKO gdy podany plik nie jest próbką z karty. Żywy audyt (`--data <shard>`) podaje PODZBIORY (shard _0006 = 3 doki, slice = 2211) → sztywne `records` = fałszywy FAIL na każdym realnym uruchomieniu, sprzeczny z celem C1. `records` jest `required: false` w formatce v1 → pominięcie legalne, `want_n=None` omija liczenie.
- **`sha256` pliku**: ODRZUCONE — brak jednego stałego wejścia (fixture vs wiele shardów); `integrity` daje INFO „pominięto".

## Konsekwencje (+ / −)
+ Ta sama `card.yaml` audytuje fixture (ścieżka CI) I dowolny realny shard (żywy dowód) bez fałszywego FAIL.
+ Żywy FAIL (np. 18 PESEL) jest **uczciwy** — wynika z PII, nie z niezgodności licznika.
− Brak deklaratywnej kontroli liczby rekordów/hasza dla tej karty (świadome; total i tak liczony tylko na pełnych danych, których nie commitujemy).

## Reversibility
Trywialna: dodać `records`/`sha256`, gdy powstanie stabilny, commitowalny pełny plik. Koszt ok. 0.

## Action items
- [ ] Brak — stan docelowy dla trybu „jedna karta, wiele realnych shardów".

## Powiązania
[[../INDEX]]
