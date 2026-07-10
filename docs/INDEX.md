---
type: index
id: IDX
title: "slayer-dsbench — indeks"
status: aktywny
author: Arkadiusz Słota
date: 2026-07-10
created_at: 2026-07-10
---

# slayer-dsbench — INDEX

> Bramka jakości datasetów: audytuje karty + rekordy (licencja per-źródło, PII, dedup, integralność). Aktywna nitka: **żywy audyt licencyjny SpeakLeash**. ZACZNIJ TU, potem [AGENTS.md](../AGENTS.md) (kontrakt + 4 bramki).
> Ledger poniżej jest **AUTO** — źródło prawdy = frontmatter węzłów. Nowy węzeł: skopiuj `_TEMPLATE.md`, nadaj `id`, uruchom `python scripts/generate-ledger.py`.

<!-- LEDGER:START (auto: scripts/generate-ledger.py; NIE EDYTUJ RĘCZNIE) -->
> **Ledger** (auto, 10 węzłów). NIE edytuj ręcznie — `scripts/generate-ledger.py`.

### Cele
| id | cel | status | plik |
|---|---|---|---|
| C1 | Żywy audyt licencyjny SpeakLeash bramką slayer-dsbench | aktywny | [C1](00-Cele/C1-Zywy-Audyt-Licencyjny-Speakleash.md) |

### Nitki dialektyczne (Teza ↔ Antyteza → Synteza)
| Teza | Antyteza | Synteza | status |
|---|---|---|---|
| [T1](10-Tezy/T1-Manifest-Per-Zrodlo-Wystarcza.md) | [AT1](15-Antytezy/AT1-Manifest-To-Za-Malo.md) | [S1](25-Syntezy/S1-Dwupoziomowa-Bramka-Plus-Pii.md) | propozycja |

### Decyzje (ADR)
| id | tytuł | status | plik |
|---|---|---|---|
| D1 | SPDX 76 źródeł zostaje UNKNOWN → audyt PASS+WARN (nie FAIL) | zaakceptowana | [D1](20-Decyzje/D1-Spdx-Unknown-To-Warn.md) |
| D2 | Port silnikowej bramki per-źródło Bartka — ODŁOŻONY (brak kodu lokalnie) | zaakceptowana | [D2](20-Decyzje/D2-Port-Bramki-Bartka-Odlozony.md) |
| D3 | Fixture w repo = syntetyczny (realne nazwy źródeł), NIE verbatim SpeakLeash | zaakceptowana | [D3](20-Decyzje/D3-Fixture-Syntetyczny-Nie-Verbatim.md) |
| D4 | Karta speakleash bez `records` i `sha256` (integrity liczy total na --data) | zaakceptowana | [D4](20-Decyzje/D4-Karta-Bez-Records-Sha256.md) |

### Pozostałe węzły (reference / runbook / ewaluacja / …)
| id | typ | tytuł | status | plik |
|---|---|---|---|---|
| R1 | reference | Inwentarz danych SpeakLeash na dysku + ograniczenia środowiska | aktywny | [R1](60-Reference/R1-Inwentarz-Danych-Speakleash.md) |
| EVAL | ewaluacja | Stan projektu — żywy audyt SpeakLeash | zywy-dokument | [EVAL](90-Ewaluacja/Stan.md) |
<!-- LEDGER:END -->

## ⭐ Ewaluacja
[[90-Ewaluacja/Stan]] — co działa (z liczbą), dowody, pętla empiryczna, co się zmienia. **Rdzeń, nie dodatek** — aktualizuj po każdym istotnym kroku.
