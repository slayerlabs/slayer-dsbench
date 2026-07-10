---
type: synteza
id: S1
title: "Dwupoziomowa bramka: manifest (WARN gdy UNKNOWN) + niezależny check PII (twardy FAIL)"
status: propozycja
parents: ["T1", "AT1"]
synthesizes: ["T1", "AT1"]
author: Arkadiusz Słota
date: 2026-07-10
created_at: 2026-07-10
---

# S1 — Dwupoziomowa bramka: manifest + PII

## Synteza
Zmienna kontekstowa = **pokrycie manifestu realnym SPDX**. To nie binarny wybór „manifest vs skrypt Bartka":
- Pokrycie = 0 (dziś, 76 źródeł UNKNOWN): bramka działa w trybie **sygnalizacyjnym** — per-source summary + WARN „UNKNOWN"; PASS nie jest blokowany (nie udajemy wiedzy, której nie mamy — D1).
- Pokrycie > 0 z rozpoznanym NC/ND: **twardy FAIL** (T1 ma rację — próg „każdy otwarty").
- Niezależnie od licencji: check PII/empty jedzie **na treści** i FAIL-uje na realnym zatruciu (AT1/N3 ma rację — to osobny wymiar).

Nasza bramka = warstwa struktury (CI-owalna, deklaratywna); skrypt Bartka = warstwa źródłowej prawdy SPDX. Łączymy je przez D2 (port) + D1 (mapa SPDX).

## Kryterium obalenia (POMIAR / DOWÓD — próg z góry)
Na realnym SpeakLeash bramka MUSI (progi ustalone PRZED uruchomieniem):
1. **PASS** gdy 0 rekordów restricted (NC/ND) I 0 PESEL.
2. **FAIL** gdy co najmniej 1 rekord NC/ND LUB co najmniej 1 PESEL.

Falsyfikacja: gdyby realny slice z PESEL dał PASS, albo czysty fixture dał FAIL bez powodu — synteza upada.

Wynik (2026-07-10): fixture (0 restricted, 0 PII) = PASS; realny shard _0006 (0 PII) = PASS; realny slice 2211 dok. = FAIL na 18 PESEL. **Warunek NIE obalił syntezy.** Luka: pkt „FAIL na NC/ND" niesprawdzony empirycznie, bo brak realnych SPDX (UNKNOWN to nie NC/ND) — zostaje otwarty do domknięcia po D1.

## Powiązania
[[../10-Tezy/T1-Manifest-Per-Zrodlo-Wystarcza]] ↔ [[../15-Antytezy/AT1-Manifest-To-Za-Malo]]
