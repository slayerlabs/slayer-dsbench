# slayer-dsbench (próbny)

Bramka **CI + formatka** do walidacji datasetów. Ktoś wrzuca **kartę datasetu** (PR), CI weryfikuje pola i jakość → zielone/czerwone. Silnik jest **schema-agnostyczny**: podmiana formatki nie dotyka kodu.

> Próbne repo. Jak dojrzeje → scala się z głównym repo datasetów. Notatki badawcze (dialektyka + bramki): `PrivateSlayNotes/01_ArekSłota/08_07_Datasety-CI-Formatka`.

## Instalacja
```bash
pip install -e .          # jedyna zależność: pyyaml
```

## Użycie
```bash
dsbench audit    --card datasets/sejm/card.yaml --format formats/v1.yaml
dsbench validate --card datasets/sejm/card.yaml            # tylko schema (pola/typy/enum)
dsbench card     --card datasets/sejm/card.yaml            # raport-karta (markdown)
dsbench init     datasets/moj-dataset                      # szkielet karty
dsbench checks                                             # lista checków
```
`audit` zwraca kod wyjścia **0=PASS / 1=FAIL** → nadaje się wprost na bramkę CI.

## Formatka (`formats/v1.yaml`) — deklaratywna
- `card_schema` — pola karty (name, version, **license**, **visibility: internal|external**, source_url, sha256, sample…).
- `record_schema` — pola rekordu (per-dokument): typ, `required`, `enum`.
- `text_field` — które pole to tekst (checki to czytają, nie kod).
- `checks` — lista checków po ID: `license, pii, dedup, decontam, stats, integrity`.

**Podmiana formatki = inny plik**, silnik bez zmian (patrz `formats/v2.yaml` — dodane wymagane `speaker_count`).

## Architektura (3 warstwy — jedna prawda)
- **Rdzeń** (`dsbench/engine.py` + `checks/`) — biblioteka, testowalna.
- **CLI** (`dsbench/cli.py`) — cienki adapter (lokalny pre-check).
- **CI** (`.github/workflows/validate.yml`) — cienki adapter (ten sam silnik + bramka na PR).

### Modularność (open/closed)
- **Pola** → deklaratywne w formatce (0 kodu przy zmianie).
- **Reguły proceduralne** (PII/dedup/dekontaminacja/licencja/stats/integrity) → **pluginy w rejestrze**: nowy check = nowy plik w `dsbench/checks/` + `@check("id")` + wpis w `checks/__init__.py`. Silnik nietknięty.

## Kontrybucja datasetu
1. `dsbench init datasets/<nazwa>` → uzupełnij `card.yaml` (URL, licencja, visibility) + wklej `sample.jsonl` (próbka).
2. `dsbench audit --card datasets/<nazwa>/card.yaml` → zielone lokalnie.
3. PR → CI odpala **ten sam** audyt (bramka). Czerwone = konkret co poprawić.

## Reguły bramki (MVP)
- **BŁĄD (FAIL):** brak wymaganego pola, zły typ/enum, `external` bez licencji, PESEL w danych, duplikaty, nakładka z eval-setem, niezgodne sha256.
- **OSTRZEŻENIE:** email/telefon w danych, licencja nie-SPDX, `internal` bez licencji.
- **INFO:** statystyki, sha256 OK/pominięte.

## Dane i integralność
Repo trzyma **kartę + URL + próbkę**, nie surowe dane (duże/poufne). `sha256` w karcie wykrywa podmianę. `visibility: internal` → CI nie pobiera pełnych danych (waliduje próbkę + metadane).

## Testy
```bash
python tests/test_dsbench.py     # bez pytest; zawiera kryteria S1/S2/S3
```
