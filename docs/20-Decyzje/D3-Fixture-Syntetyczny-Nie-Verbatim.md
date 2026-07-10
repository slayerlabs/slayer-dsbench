---
type: decyzja
id: D3
title: "Fixture w repo = syntetyczny (realne nazwy źródeł), NIE verbatim SpeakLeash"
status: zaakceptowana
parents: ["C1"]
implements: ["S1"]
author: Arkadiusz Słota
date: 2026-07-10
created_at: 2026-07-10
data_decyzji: 2026-07-10
---

# D3 — Fixture syntetyczny, nie verbatim

## Decyzja
`datasets/speakleash/sample.jsonl` (commitowany, ćwiczy CI) to tekst **syntetyczny** z **realnymi nazwami źródeł**. Verbatim realny tekst SpeakLeash audytujemy tylko LOKALNIE, bez commitu.

## Rozważone alternatywy
- **Wrzucić realny tekst SpeakLeash do fixture**: ODRZUCONE — repo `slayerlabs/slayer-dsbench` jest publiczne; commit realnego tekstu o UNKNOWN/potencjalnie niewolnej licencji to dokładnie „zatrucie", przed którym broni bramka. Logika działa na `source`, więc syntetyk w pełni ćwiczy grupowanie.

## Konsekwencje (+ / −)
+ Publiczne repo czyste licencyjnie; CI deterministyczne (gwarantowany fixture).
+ Werdykt CI zależy WYŁĄCZNIE od fixture (realny live może FAIL-ować na PII — to lokalne evidence, nie CI).
− Fixture nie oddaje realnej dystrybucji treści (świadome; realia mierzymy lokalnie — R1).

## Reversibility
Trywialna: podmiana `sample.jsonl`. Koszt ok. 0.

## Action items
- [ ] (opcjonalnie) rozszerzyć fixture o więcej źródeł/kształtów, wciąż syntetycznie.

## Powiązania
[[../INDEX]]
