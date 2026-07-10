---
type: decyzja
id: D2
title: "Port silnikowej bramki per-źródło Bartka — ODŁOŻONY (brak kodu lokalnie)"
status: zaakceptowana
parents: ["C1"]
implements: ["S1"]
author: Arkadiusz Słota
date: 2026-07-10
created_at: 2026-07-10
data_decyzji: 2026-07-10
---

# D2 — Port bramki Bartka odłożony

## Decyzja
Port bramki per-źródło Bartka (blob-level, dynaword) do `dsbench/checks/` jest ODŁOŻONY. Powód: kodu nie ma lokalnie — `polish-dynaword` na dysku to same pliki `.parquet`, zero kodu/skryptów. Nie wolno go zmyślać.

## Rozważone alternatywy
- **Zrekonstruować bramkę Bartka „ze zrozumienia"**: ODRZUCONE — to byłby zgadywany kontrakt, ryzyko rozjazdu z jego liczeniem (AT1/N2).

## Konsekwencje (+ / −)
+ Nasza bramka (manifest + per-rekord) stoi niezależnie i już audytuje realne dane.
− Warstwa źródłowej prawdy SPDX Bartka nie jest jeszcze zintegrowana — proxy zostaje proxy.

## Reversibility
Nie dotyczy — to odłożenie, nie zmiana architektury. Odblokowuje je dostarczenie kodu/URL repo.

## Action items
- [ ] Uzyskać URL repo / wklejenie kodu bramki Bartka (issue `maggi-ju0`).
- [ ] Sportować 1:1 do `dsbench/checks/`, apple-to-apple z naszym per-rekord.

## Powiązania
[[../INDEX]] · issue: `maggi-ju0`
