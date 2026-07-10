---
type: decyzja
id: D1
title: "SPDX 76 źródeł zostaje UNKNOWN → audyt PASS+WARN (nie FAIL)"
status: zaakceptowana
parents: ["C1"]
implements: ["S1"]
rejects: ["AT1"]
author: Arkadiusz Słota
date: 2026-07-10
created_at: 2026-07-10
data_decyzji: 2026-07-10
---

# D1 — SPDX 76 źródeł zostaje UNKNOWN (PASS+WARN)

## Decyzja
`datasets/speakleash/sources.yaml` trzyma 76 źródeł jako `UNKNOWN`. Audyt = PASS + WARN (UNKNOWN nie blokuje). Realne SPDX per źródło wpiszemy dopiero z mapą od Bartka.

## Rozważone alternatywy
- **Zmyślić SPDX „na oko"**: ODRZUCONE — bramka broni przed zatruciem, więc nie wolno jej karmić zgadywaną licencją; to byłoby fałszywe zielone albo fałszywe czerwone.
- **UNKNOWN → FAIL (twardo)**: ODRZUCONE — zablokowałoby CI na wszystkim, zanim mamy dane; UNKNOWN to „nie wiem", nie „niewolne". Intencja: UNKNOWN → WARN sygnalizuje brak, NC/ND → FAIL blokuje realne zatrucie.

## Konsekwencje (+ / −)
+ CI zielone, per-source summary widoczne, zero zmyślania.
+ Ścieżka twardego FAIL gotowa — wystarczy podmienić UNKNOWN na realne SPDX (zero zmian w kodzie).
− Do czasu mapy Bartka twardy FAIL na NC/ND jest niesprawdzony na realu (luka w S1).

## Reversibility
Trywialna: edycja `sources.yaml` (źródło → SPDX). Koszt ok. 0.

## Action items
- [ ] Pozyskać mapę SPDX 76 źródeł od Bartka (issue `maggi-c2i`).
- [ ] Po wpisaniu: re-audyt, domknąć warunek obalenia S1 (FAIL na NC/ND).

## Powiązania
[[../INDEX]] · issue: `maggi-c2i`
