---
type: teza
id: T1
title: "Manifest źródło→SPDX + reguła per-rekord wystarcza do bramkowania kompilacji"
status: częściowo-zweryfikowana
parents: ["C1"]
author: Arkadiusz Słota
date: 2026-07-10
created_at: 2026-07-10
---

# T1 — Manifest źródło→SPDX wystarcza do bramkowania kompilacji

## Teza
Do bramkowania licencyjnego kompilacji wieloźródłowej wystarczy: (a) mapa `źródło → SPDX` w `sources.yaml` obok karty, (b) reguła per-rekord w bramce, która grupuje po polu `source` i pod `visibility: external` wymaga, by **każdy** dokument był otwarty (NC/ND/zamknięty = FAIL). Licencja rekordu wygrywa, manifest uzupełnia.

## Argumenty PRO
- A1: Logika działa na polu `source`/`license`, **nie na treści** → nie trzeba trzymać realnego tekstu, by ćwiczyć bramkę (patrz D3).
- A2: Rekord bez licencji → parasol karty (pełna wsteczna zgodność ze starymi datasetami).
- A3: Jeden zatruty dokument (NC/ND) zapala FAIL — próg „każdy musi być otwarty" jest twardy, nie uśredniający.
- A4: Zero hardkodu pól — nazwy (`license_field`, `source_field`) czytane z formatki, więc silnik pozostaje generyczny.

## Dlaczego to nie oczywiste
Naiwnie: jedna `license` na karcie. To uśrednia licencje i przepuszcza zatrucie. Per-rekord + manifest przenosi granulację tam, gdzie licencja NAPRAWDĘ żyje (źródło).

## Status weryfikacji
Częściowo zweryfikowana: fixture 6 źródeł = PASS, realny shard _0006 = PASS, multi-źródłowy realny = FAIL na PII (bramka reaguje). Twardy FAIL na NC/ND niesprawdzony empirycznie — dziś 76 źródeł to UNKNOWN (tylko WARN); patrz AT1/D1.

## Antyteza ↔ Synteza
[[../15-Antytezy/AT1-Manifest-To-Za-Malo]] → [[../25-Syntezy/S1-Dwupoziomowa-Bramka-Plus-Pii]]
