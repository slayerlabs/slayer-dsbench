# Jak dodać dataset

Dataset dodajesz przez **PR**. CI (bramka) sprawdza kartę i jakość — zielone = merge, czerwone = konkret co poprawić. Ten sam audyt uruchomisz lokalnie **przed** PR, żeby mieć zielone od razu.

## 0. Setup (raz)
```bash
pip install -e .          # jedyna zależność: pyyaml
```

## 1. Szkielet karty
```bash
dsbench init datasets/<nazwa>
```
Powstaje `datasets/<nazwa>/card.yaml` + `sample.jsonl`.

## 2. Uzupełnij kartę (`card.yaml`)
| pole | opis | wymagane |
|---|---|---|
| `name`, `version` | identyfikacja | ✅ |
| `license` | licencja **tekstu/danych** (SPDX, np. `CC0-1.0`) | ✅ |
| `collection_license` | licencja **kolekcji/metadanych** (domyślnie `CC0-1.0`) | — |
| `visibility` | `external` (publiczny, otwarta licencja) lub `internal` | ✅ |
| `source_url` | gdzie leżą **pełne dane** (HF / release) | ✅ |
| `sample` | plik próbki w repo (np. `sample.jsonl`) | ✅ |
| `sha256` | suma kontrolna pełnego pliku danych (integralność) | — |
| `records`, `bytes` | rozmiar całości | — |

> **Nie commituj surowych danych** (duże/poufne). Repo trzyma **kartę + URL + próbkę**; CI może pobrać pełne dane po `source_url` i sprawdzić `sha256`.

## 3. Wklej próbkę (`sample.jsonl`)
Kilkadziesiąt–100 rekordów, **per-dokument**, JSON Lines. Wymagane pole: `text`; zalecane: `id` (unikalne). Przykład:
```json
{"id": "x-0001", "text": "…", "date": "2024-01-17", "word_count": 9}
```
Pola rekordu definiuje formatka (`formats/v1.yaml` → `record_schema`).

> **Licencja per-dokument (opcjonalna).** Gdy dataset łączy **wiele źródeł o różnych licencjach** (styl speakleash/dynaword), dołóż do rekordu `source` i `license` (SPDX). Bramka grupuje licencje **per źródło**; pod `external` **każdy** dokument musi być otwarty — jeden NC/ND/zamknięty = FAIL. Rekord bez `license` dziedziczy `license` z karty (parasol).

## 4. Sprawdź lokalnie (zielone przed PR)
```bash
dsbench audit --card datasets/<nazwa>/card.yaml --format formats/v1.yaml
```
Kod wyjścia `0` = PASS, `1` = FAIL.

## 5. PR
Otwórz PR. CI odpali **ten sam** audyt + testy silnika. Uzupełnij checklistę z szablonu PR.

## Reguły bramki
- **BŁĄD (FAIL):** brak wymaganego pola / zły typ / zły enum · `external` bez otwartej licencji · **dokument per-rekord z licencją NIE-otwartą (NC/ND/zamknięta)** pod `external` · **PESEL** w danych · **duplikaty treści** · **nakładka z eval-setem** · niezgodne `sha256` · niezgodna liczba rekordów · zduplikowane `id` · pusty `text`.
- **OSTRZEŻENIE:** email/telefon w danych · licencja nie-SPDX (karta lub per-dok) · `internal` bez licencji.
- **INFO:** statystyki, licencje, `sha256` OK/pominięte.

## Wewnętrzne vs zewnętrzne
- `visibility: external` — publiczny, **wymagana otwarta licencja** (CI wymusza).
- `visibility: internal` — dane prywatne; CI **nie pobiera** pełnych danych, waliduje próbkę + metadane. Nie wrzucaj poufnych danych do publicznego repo.

## Dekontaminacja
Eval-sety trzymamy jako **hashe** (`eval_sets/hashes.txt`), nie surowe dane. Nakładka Twojego datasetu z eval-setem = błąd (chroni przed „powołaniem się" modelu na test).
