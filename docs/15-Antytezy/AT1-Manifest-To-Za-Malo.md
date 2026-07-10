---
type: antyteza
id: AT1
title: "Manifest to za mało — UNKNOWN nie blokuje, licencja bywa per-blob (steelman)"
status: w-dyskusji
parents: ["T1"]
author: Arkadiusz Słota
date: 2026-07-10
created_at: 2026-07-10
---

# AT1 — Manifest to za mało (steelman)

## Antyteza (najmocniejsza wersja, co najmniej 3 punkty — NIE strawman)
1. N1: Dopóki 76 źródeł to `UNKNOWN`, bramka daje tylko WARN — realne zatrucie licencyjne **przechodzi jako PASS**. Manifest bez realnych SPDX to teatr: struktura jest, twardego FAIL na NC/ND nie ma czym wywołać.
2. N2: W SpeakLeash/dynaword licencja bywa per **blob** (plik-źródło), nie per rekord; Bartek ma własny skrypt liczący ją per-źródło + własne bramki. Nasze grupowanie po polu `source` to **proxy** jego liczenia — może się rozjechać (inne granice źródła, inne mapowanie).
3. N3: Licencja to nie jedyny wektor zatrucia. Realny SpeakLeash niesie PII (PESEL, e-mail, telefon). Bramka licencyjna, choćby idealna, nie chroni przed tym — potrzebny osobny, ZMIERZONY check.
4. N4: Fixture syntetyczny dowodzi tylko mechaniki grupowania, nie realnej dystrybucji licencji/treści. „Żywy audyt" na 3 dokach jednego źródła to wąska próbka, by mówić o SpeakLeash jako całości.

## Granica (kiedy / dlaczego nie)
Gdy realne SPDX są wpisane, a `source` w rekordach 1:1 pokrywa granice źródeł Bartka — wtedy manifest wystarcza i N1/N2 słabną. N3 zostaje **zawsze** (PII to inny wymiar). N4 słabnie z każdym realnie zaudytowanym shardem.

## Powiązania
teza: [[../10-Tezy/T1-Manifest-Per-Zrodlo-Wystarcza]] · synteza: [[../25-Syntezy/S1-Dwupoziomowa-Bramka-Plus-Pii]]
