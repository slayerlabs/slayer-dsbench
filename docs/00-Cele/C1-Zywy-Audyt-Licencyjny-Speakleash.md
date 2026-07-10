---
type: cel
id: C1
title: "Żywy audyt licencyjny SpeakLeash bramką slayer-dsbench"
status: aktywny
parents: []
author: Arkadiusz Słota
date: 2026-07-10
created_at: 2026-07-10
---

# C1 — Żywy audyt licencyjny SpeakLeash bramką slayer-dsbench

## Po co / dla kogo
Dla zespołu Slayer + Bartka Kobylińskiego (SpeakLeash). Realny blob treningowy (SpeakLeash, polish-dynaword) to **kompilacja wielu źródeł o RÓŻNYCH licencjach**. Karta datasetu z jedną `license` uśrednia je — kompilacja zawierająca choćby jedno źródło NC/ND „przechodzi" pod parasolem = **zatrucie licencyjne**. Cel: bramka, która audytuje licencję **per źródło** i którą da się uruchomić na **żywym** SpeakLeash (wymóg Bartka z Discorda: „na tym de facto mielibyśmy się opierać").

## Sukces (mierzalny)
1. `datasets/speakleash/` jest audytowanym datasetem w CI (`dsbench audit --card` = PASS, exit 0).
2. Bramka uruchomiona na **realnych** rekordach SpeakLeash (nie tylko fixture) — z obserwowalnym per-source summary.
3. Bramka **FAIL-uje** na realnym zatruciu (NC/ND lub PII) — nie jest atrapą.

## Kryterium falsyfikowalne
Cel chybiony, jeśli: bramka daje PASS na realnym SpeakLeash zawierającym dokument NC/ND albo PESEL (fałszywe zielone), ALBO nie da się jej uruchomić na realnych danych (tylko na syntetyku).

## Zakres (JEST / NIE w MVP)
JEST: audyt licencji per-źródło przez manifest `sources.yaml`; PII/empty/dedup na realnych rekordach; dekompresja shardów `.zst`.
NIE: port silnikowej bramki Bartka (brak kodu lokalnie → D2); realne SPDX 76 źródeł (czeka na Bartka → D1); dataset Piotra (osobna nitka `maggi-dvp`).

## Nitki
[[../10-Tezy/T1-Manifest-Per-Zrodlo-Wystarcza]] ↔ [[../15-Antytezy/AT1-Manifest-To-Za-Malo]] → [[../25-Syntezy/S1-Dwupoziomowa-Bramka-Plus-Pii]]
Decyzje: [[../20-Decyzje/D1-Spdx-Unknown-To-Warn]] · [[../20-Decyzje/D2-Port-Bramki-Bartka-Odlozony]] · [[../20-Decyzje/D3-Fixture-Syntetyczny-Nie-Verbatim]] · [[../20-Decyzje/D4-Karta-Bez-Records-Sha256]]

## Powiązania
[[../INDEX]]
