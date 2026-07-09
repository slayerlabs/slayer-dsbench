# slayer-dsbench

**Bramka CI + formatka do walidacji datasetów.** Kontrybutor wrzuca **kartę datasetu** (PR), a CI weryfikuje pola i higienę → ✅/❌. Silnik jest **schema-agnostyczny**: podmiana formatki nie dotyka kodu.

> Repo w fazie próbnej. Gdy dojrzeje → scala się z głównym repozytorium datasetów. Decyzje projektowe i research prowadzone są w wewnętrznych notatkach (dialektyka + bramki jakości).

## Po co
Bez wspólnej formatki każdy opisuje dataset po swojemu (brak licencji, niespójne pola, śmieć w danych → zatruty trening). Ta bramka wymusza spójność **u źródła**: jeśli karta nie spełnia formatki albo dane mają problem (PII, duplikaty, nakładka z eval-setem), PR nie przechodzi.

## Szybki start
```bash
pip install -e .                                              # jedyna zależność: pyyaml
dsbench audit --card datasets/sejm/card.yaml                  # pełny audyt (0=PASS / 1=FAIL)
dsbench init  datasets/moj-dataset                            # szkielet karty
dsbench checks                                                # lista checków
```

## Dodanie datasetu
Pełna instrukcja: **[CONTRIBUTING.md](CONTRIBUTING.md)**. W skrócie: `dsbench init` → uzupełnij `card.yaml` + wklej `sample.jsonl` → `dsbench audit` (zielone) → PR.

## Reguły bramki
| poziom | co |
|---|---|
| ❌ **FAIL** | brak wymaganego pola / zły typ / zły enum · `external` bez otwartej licencji · **PESEL** · **duplikaty treści** · **nakładka z eval-setem** · niezgodne `sha256`/liczba rekordów · zduplikowane `id` · pusty `text` |
| ⚠️ **WARN** | email/telefon w danych · licencja nie-SPDX · `internal` bez licencji |
| ℹ️ **INFO** | statystyki, licencje, `sha256` |

## Formatka (`formats/v1.yaml`) — deklaratywna
- `card_schema` / `record_schema` — pola, typy, `required`, `enum` (per-dokument).
- `text_field`, `id_field` — które pola są tekstem/ID (checki to czytają, nie kod).
- `checks` — lista po ID: `license · uniqueid · empty · pii · dedup · decontam · stats · integrity`.

**Podmiana formatki = inny plik**, silnik bez zmian (porównaj `v1.yaml` ↔ `v2.yaml`).

## Architektura (3 warstwy, jedna prawda)
- **Rdzeń** (`dsbench/engine.py` + `checks/`) — biblioteka, testowalna.
- **CLI** (`dsbench/cli.py`) — cienki adapter (lokalny pre-check).
- **CI** (`.github/workflows/validate.yml`) — cienki adapter (ten sam silnik na PR).

**Modularność (open/closed):** pola → deklaratywne w formatce (0 kodu przy zmianie); reguły proceduralne → pluginy w rejestrze (`@check`, nowy plik → wpis w `checks/__init__.py`, silnik nietknięty).

## Dane i integralność
Repo trzyma **kartę + `source_url` + próbkę**, nie surowe dane (duże/poufne). `sha256` wykrywa podmianę. `visibility: internal` → CI nie pobiera pełnych danych. Eval-sety do dekontaminacji trzymane jako **hashe** (`eval_sets/hashes.txt`).

## Testy
```bash
python tests/test_dsbench.py     # bez pytest; zawiera kryteria S1 (modularność) / S2 (integralność) / S3 (spójność)
```

## Licencja
Kod: patrz `LICENSE` (jeśli dodany). Karty datasetów: dwupoziomowo — tekst = licencja źródła, kolekcja/metadane = CC0.
