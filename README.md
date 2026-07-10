# slayer-dsbench

**Bramka CI + formatka do walidacji datasetów.** Kontrybutor wrzuca **kartę datasetu** (PR), CI weryfikuje pola i higienę → ✅/❌. Silnik jest **schema-agnostyczny**: podmiana formatki nie dotyka kodu.

> Repo w fazie próbnej. Gdy się sprawdzi → wpinamy je do docelowej bazy datasetów (patrz „Migracja"). Decyzje projektowe i research prowadzone są w wewnętrznych notatkach.

---

## Po co mi to?

**Bez bramki:** każdy opisuje dataset po swojemu — jeden ma licencję, drugi nie; jeden opisuje źródło, drugi rekord; ktoś wrzuci dane ze śmieciem (PESEL, duplikaty, fragment eval-setu) i **zatruje trening** — a wyjdzie to dopiero, gdy „ktoś się powoła". Efekt: chaos i mit.

**Z bramką:** jedna **formatka** (kontrakt) + **CI**, które na PR sprawdza kartę i jakość. Dataset wchodzi tylko, jeśli przejdzie. Recenzja = spojrzenie na zielone/czerwone, nie ręczne dłubanie w cudzym pliku.

Dla kogo: **kontrybutorzy** (wewn./zewn.), osoba **utrzymująca bazę**, i **trening downstream** (dostaje dane o znanej higienie i licencji).

---

## Jak z tym działać (end-to-end)

```bash
pip install -e .          # jedyna zależność: pyyaml
```

**1. Szkielet karty** dla nowego datasetu:
```bash
dsbench init datasets/moj-dataset
```
**2. Uzupełnij** `datasets/moj-dataset/card.yaml` (nazwa, licencja, `visibility`, `source_url`, `sample`) i wklej próbkę do `sample.jsonl` (per-dokument, pole `text` wymagane, `id` unikalne).

**3. Sprawdź lokalnie** — zielone przed PR:
```bash
dsbench audit --card datasets/moj-dataset/card.yaml
```
Zielone (kod wyjścia `0`):
```
## dsbench: sejm-speeches — ✅ PASS
- ℹ️ [license]  card: licencja tekstu: CC0-1.0
- ℹ️ [uniqueid] data: 'id' unikalne (4)
- ℹ️ [dedup]    data: duplikaty: 0
- ℹ️ [decontam] data: nakładki z eval-setami: 0
```
Czerwone (kod wyjścia `1` → CI zablokuje merge):
```
## dsbench: ... — ❌ FAIL
- ❌ [schema]  record#0: brak wymaganego pola 'text'
- ❌ [license] card: external BEZ licencji tekstu
- ❌ [pii]     data: PESEL wykryty: 3 — zredaguj
```
**4. PR** — CI odpala **ten sam** audyt + testy silnika. Czerwone = konkret co poprawić. Pełna instrukcja: **[CONTRIBUTING.md](CONTRIBUTING.md)**.

Inne komendy: `dsbench validate` (tylko schema), `dsbench card` (raport md), `dsbench checks` (lista checków).

---

## Reguły bramki
| poziom | co |
|---|---|
| ❌ **FAIL** | brak pola / zły typ / zły enum · `external` bez otwartej licencji · **dokument per-rekord z licencją NIE-otwartą (NC/ND/zamknięta)** pod `external` · **PESEL** · **duplikaty treści** · **nakładka z eval-setem** · niezgodne `sha256`/liczba rekordów · zduplikowane `id` · pusty `text` |
| ⚠️ **WARN** | email/telefon · licencja nie-SPDX (karta lub per-dok) · `internal` bez licencji |
| ℹ️ **INFO** | statystyki, licencje, **rozkład licencji per źródło**, `sha256` |

## Formatka (`formats/v1.yaml`) i modularność
Deklaratywna: `card_schema` / `record_schema` (pola, typy, `required`, `enum`), `text_field`/`id_field`, `license_field`/`source_field`, lista `checks`.
**Podmiana formatki = inny plik, silnik bez zmian** (porównaj `v1.yaml` ↔ `v2.yaml`). Pola → deklaratywne (0 kodu przy zmianie); reguły proceduralne → pluginy w rejestrze (`@check`; nowy plik → wpis w `checks/__init__.py`).

**Licencja dwupoziomowa (dynaword).** Karta niesie *parasol* — `license` (tekst) + `collection_license` (metadane). Ale realny blob to **kompilacja wielu źródeł o różnych licencjach**, więc licencja bywa **per dokument/źródło**: dołóż w `sample.jsonl` pola `license` (SPDX) i `source`, a formatka wskaże je przez `license_field`/`source_field`. Pod `external` **każdy** dokument musi być otwarty — jeden NC/ND/zamknięty = ❌ (chroni przed zatruciem licencyjnym); bramka raportuje rozkład licencji per źródło. Rekord bez `license` dziedziczy parasol karty (pełna wsteczna zgodność).

**Licencja per-źródło przez manifest (`sources.yaml`).** Gdy rekordy niosą tylko `source` (bez `license`) — jak realny SpeakLeash/dynaword — dołóż obok karty plik `sources.yaml` (mapa `źródło → {license: SPDX}`, forma zagnieżdżona lub płaska `{źródło: SPDX}`) i wskaż go w karcie: `source_manifest: sources.yaml`. Bramka rozwiązuje licencję per źródło z manifestu; **precedencja: licencja rekordu > manifest > parasol karty**. Reguły egzekucji bez zmian (NC/ND → ❌, nierozpoznane/`UNKNOWN` → ⚠️ pod `external`). `source_manifest` wskazany, a pliku brak → ❌.

---

## Migracja do docelowej bazy datasetów

To repo jest **próbne**. Gdy bramka się sprawdzi, wpinamy ją do właściwego repo datasetów. Bo silnik jest **schema-agnostyczny**, migracja jest tania — docelowe repo może mieć **własną formatkę**, a silnik zostaje bez zmian.

**Opcja A — `dsbench` jako pakiet (rekomendowana).**
Docelowe repo NIE kopiuje silnika — instaluje go w CI:
```yaml
# .github/workflows/validate.yml w DOCELOWYM repo
- run: pip install "git+https://github.com/slayerlabs/slayer-dsbench@v0.1.0"
- run: |
    fail=0
    for card in $(find datasets -name card.yaml); do
      dsbench audit --card "$card" --format formats/v1.yaml || fail=1
    done
    exit $fail
```
Docelowe repo trzyma tylko: `datasets/<name>/{card.yaml,sample.jsonl}`, `formats/v1.yaml` (kontrakt), `eval_sets/hashes.txt`, workflow. Silnik wersjonowany osobno (`@v0.1.0`) → aktualizacja bramki = bump wersji, dane nietknięte.

**Opcja B — wchłonięcie.**
Skopiuj katalog `dsbench/` do docelowego repo jako narzędzie (bez osobnego pakietu). Prościej, ale kopia silnika żyje w repo (aktualizacje trzeba synchronizować ręcznie).

**Co przenosisz (obie opcje):**
- `formats/*.yaml` — kontrakt (dostosuj pola pod realną bazę; **silnik bez zmian**),
- `.github/workflows/validate.yml` — bramka (popraw ścieżki, jeśli inne),
- `eval_sets/hashes.txt` — cele dekontaminacji,
- opcjonalnie `datasets/*/` — jeśli zabierasz przykładowe karty.

**Kroki:**
1. W docelowym repo dodaj `formats/v1.yaml` + workflow (Opcja A: `pip install git+…`).
2. Skonwertuj istniejące datasety na karty (`dsbench init` + uzupełnij) — jeden PR per dataset.
3. Włącz bramkę jako **required check** na PR (Settings → Branches → Branch protection).
4. (opcja) Dostosuj formatkę pod realne pola bazy — dzięki modularności silnik zostaje ten sam.

---

## Architektura (3 warstwy, jedna prawda)
- **Rdzeń** (`dsbench/engine.py` + `checks/`) — biblioteka, testowalna.
- **CLI** (`dsbench/cli.py`) — cienki adapter (lokalny pre-check).
- **CI** (`.github/workflows/validate.yml`) — cienki adapter (ten sam silnik na PR).

## Dane i integralność
Repo trzyma **kartę + `source_url` + próbkę**, nie surowe dane (duże/poufne). `sha256` wykrywa podmianę. `visibility: internal` → CI nie pobiera pełnych danych. Eval-sety trzymane jako **hashe**.

## Testy
```bash
python tests/test_dsbench.py     # bez pytest; kryteria S1 (modularność) / S2 (integralność) / S3 (spójność CI↔lokalnie)
```
