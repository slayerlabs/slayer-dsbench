# CLEANING — pipeline czyszczenia korpusu PL (polish-dynaword-expansion)

Know-how produkcyjnego czyszczenia HPLT→dynaword (od 2026-08-07, stan: `phone_scrub` v20).

## Pipeline (kolejność)
1. **`clean_hplt_v3.py`** — fetch HPLT `.jsonl.zst` → filtry (lang/short/MT/register/legalish/domain/domain-cap) + **PII-scrub** (poniżej) + tiktoken token_count → parquet + stats.
2. **`polish_dataset.py --apply`** — 10 klas artefaktów tekstu (Strona-header / diakryt-`?` / block-frame / leading-nav-list / bare-dash / U+FFFD / Latin-2-remap / UTF8-double-encode / garbled-drop / button-notice-asterisk).
3. **`near_dup_vs_dynaword.py`** — cross-source dedup vs baza. MinHash-128/LSH-16×8 (`--threshold`) **+ `--prefix-chars 200`** (prefix-sig-containment: łapie truncation-variants które Jaccard gubi — patrz niżej).
4. **`deep_verify.py`** — **niezależna** brama PII-safety (patrz INVARIANT).
5. **`auto_clean_mangle.py`** — trim `[Telefon]<digit>` mangle-artefaktów (bidirectional).
6. **`rescrub_drop_v17.py`** — ponowny scrub gotowego parquetu nowszą wersją `phone_scrub` + wycięcie dokumentów z mangle (cyfr zjedzonych przez wcześniejszy scrub nie da się przywrócić) + quality-pass v20 (wycięcie podpisów agencyjnych `© ℗Podpis: …`, sklejonego „OdpowiedzUsuń” i ramek z 20+ podkreśleń); strumieniowo; z `--outdir` zapis do nowego pliku, bez niego w miejscu.
7. **`drop_docs.py`** — wycięcie dokumentów po `id` z listy niezależnej bramki (krok końcowy: każdy oflagowany dokument wypada).
8. **`dedup_normalized.py`** — dedup po hashu surowego tekstu (pełny + prefiks), strumieniowo; ten sam dokument z różnych wersji scrubu łączy się, gdy scrub dał identyczny tekst.

## PII-scrub (`clean_hplt_v3.scrub_pii`)
- **phone → `[Telefon]`** (`phone_scrub.py` v20): HPLT-pii-spany + `PHONE_RE` (+48-intl, label-less) + **label-window** (labeled any-format, bounded-fixpoint) + `auto_clean_mangle`.
- **email/national-ID → `[PII]`**: `EMAIL_RE` (przez HPLT-spany) + `NATID_RE` (keyword-adjacent PESEL/NIP/REGON/dowód + ≥9-digit).
- `[Telefon]` = **semantic-tag NIE fixed-fake-number** (fake `+48 000...` poisonuje: model memoryzuje high-freq numer; tag = slot-koncept + no-digit → fixpoint convergent).

## phone_scrub v20 — guardy (v6→v20 iteracja, każdy = złapana klasa)
- **label-window 75 znaków** po etykiecie telefonu (`tel/telefon/kom/komórka/kontakt/zadzwoń/dzwoń/infolinia/gsm/fax/faks/nr tel/numer tel/telefonicznie`) **i przed nią** (numer przed etykietą, np. „(690 88 99 22) tel”).
- **`_is_phone`**: co najmniej 9 cyfr (po zdjęciu prefiksu `00`); z separatorami lub `+` do 15 cyfr (zagraniczne stacjonarne), goły ciąg do 11; wykluczone 6+ zer, KRS, daty, ISBN.
- **separatory między grupami `[ \t\-/]{0,3}`, bez kropki** → łapie „504 - 729 098”, nie rusza współrzędnych i liczb dziesiętnych; numer może kończyć się tuż przed datą z kropkami („… 23.13.01.2023”).
- **wiele numerów obok siebie** (rozdzielone `/`, `)(` albo spacją; przy spacji obie strony muszą być poprawnym numerem i razem ≤ 22 cyfry) → cały ciąg zastąpiony.
- **account-guard:** klaster > 13 cyfr i (≥ 24 cyfry albo słowo konto/rachunek/IBAN/BIC/SWIFT ≤ 30 znaków przed nim) → nie telefon (NRB-26, IBAN-28); dwa telefony obok siebie bez słowa o koncie są zastępowane.
- **currency-guard:** liczba, po której stoi waluta lub `%` → cena, nie telefon.
- **numer zawinięty przez `\n`** (część przed złamaniem < 9 cyfr, razem 9–11) → zastępowany.
- **bounded-fixpoint** (cap-8, convergent+guarded — NIE divergentny cascade).

## ⚠️ INVARIANT (FCD-S6): independent-lens, NIE self-report
**Residual-check PII MUSI być independent-lens SZERSZY niż scrub (`check ⊋ scrub`), NIE idempotency (`check == scrub`).** Idem re-runuje ten sam scrub → strukturalnie ślepy na to co scrub SYSTEMATYCZNIE gubi (format-recall-gap). `deep_verify.py` = independent regex+context (date/IBAN/token-excluded). Dowód: idem-residual=12 FALSE-CLEAN vs independent 2377 leak-docs (~1900 real-phone) na tym samym korpusie. Self-report DISQUALIFIED jako clear-signal; 2. arbiter z superset-recall.

## Dedup-vs-base: truncation-variants
Base=truncated-prefix kandydata → **niski Jaccard** (J≈0.2 ≪ 0.8) → MinHash-LSH-0.8 STRUKTURALNIE GUBI (3 vs 3038 na bin9). Łap **prefix-sig-containment** (md5 first-200-char norm) → `--prefix-chars 200`.

## Testy
`tests/test_phone_scrub.py` — bateria akceptacyjna phone_scrub (scrub/keep/leading-0/kom/dzwoń/newline/foreign/IBAN/FP/fixpoint, klasy v6→v20). Całe repo: `python -m pytest tests pipeline/tests`.

## Stan PII w slayer-pl-8x3b
Karta zbioru: placeholdery `[PII]`/`[Telefon]` w warstwie web pochodzą ze źródła (HPLT po czyszczeniu). Części spoza warstwy web (rdzeń, warstwa prawna) pochodzą z innych źródeł; raport z próbki przy budowie znalazł adresy e-mail głównie w nich (wystąpienia w tekście, nie liczba osób). Zbiór nie przeszedł niezależnej bramki PII na całości; pełny audyt danych osobowych karta przenosi na odbiorcę.

## Inny potok: dane Slayer1B 1.09 (dalszy trening)
Dane do 1.09 (FineWeb-Edu EN, gollem-corpus web, FinePDFs-edu pol, FineWeb-2 pol) czyszczono osobnym potokiem; jego kodu nie ma jeszcze w tym repozytorium. Różnice wobec pipeline'u powyżej:
- **PII = wycięcie całego dokumentu**, nie zastąpienie numeru placeholderem: dokument wypada przy trafieniu e-maila, telefonu PL lub US, PESEL, NIP, REGON (9 cyfr), dowodu, IBAN/NRB, karty albo SSN (identyfikatory z sumą kontrolną sprawdzane); telefony międzynarodowe i adresy IP są tylko liczone (za dużo fałszywych trafień).
- **Dane się nie zmieniają, zmieniają się listy wycięć** (plik + numer wiersza dla każdej kontroli). Listy określają pulę dopuszczonych wierszy; do kawałków wybierana jest deterministycznie część zgodnie z konfiguracją i udziałami źródeł.
- **Przecieki testów:** 13-gramy wobec benchmarków i held-outów oraz 8-gramy szablonów zadań po maskowaniu liczb; kontrola dodatnia przed każdym przebiegiem (wstrzyknięte znane próbki muszą zostać złapane).
- **Dedup w pięciu warstwach:** wobec danych poprzednich wersji modelu, wobec held-outu i walidacji, między źródłami, wewnątrz źródła, wobec faktycznej treści już zbudowanych kawałków; porównanie po sha tokenów i po odciskach tekstu (początek, koniec, całość). Warstwy 3–5 doszły w trakcie budowy: kopie w kawałku, który był już w treningu, odjęto od licznika unikatowych tokenów; późniejsze kawałki przebudowano przed treningiem.
- **Held-out** (około 1% kandydatów po filtrach, przed dedupem) odkładany przed budową kawałków; nigdy nie trafia do treningu ani do publicznych repozytoriów.
