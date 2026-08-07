# CLEANING — pipeline czyszczenia korpusu PL (polish-dynaword-expansion)

Know-how produkcyjnego czyszczenia HPLT→dynaword (sesja 2026-08-07). Para do vault FCD (`labvault 05_08_Fabryczne-Czyszczenie-Datasetow`: FCD-S5/S6/R5).

## Pipeline (kolejność)
1. **`clean_hplt_v3.py`** — fetch HPLT `.jsonl.zst` → filtry (lang/short/MT/register/legalish/domain/domain-cap) + **PII-scrub** (poniżej) + tiktoken token_count → parquet + stats.
2. **`polish_dataset.py --apply`** — 10 klas artefaktów tekstu (Strona-header / diakryt-`?` / block-frame / leading-nav-list / bare-dash / U+FFFD / Latin-2-remap / UTF8-double-encode / garbled-drop / button-notice-asterisk).
3. **`near_dup_vs_dynaword.py`** — cross-source dedup vs baza. MinHash-128/LSH-16×8 (`--threshold`) **+ `--prefix-chars 200`** (prefix-sig-containment: łapie truncation-variants które Jaccard gubi — patrz niżej).
4. **`deep_verify.py`** — **niezależna** brama PII-safety (patrz INVARIANT).
5. **`auto_clean_mangle.py`** — trim `[Telefon]<digit>` mangle-artefaktów (bidirectional).

## PII-scrub (`clean_hplt_v3.scrub_pii`)
- **phone → `[Telefon]`** (`phone_scrub.py` v12b): HPLT-pii-spany + `PHONE_RE` (+48-intl, label-less) + **label-window** (labeled any-format, bounded-fixpoint) + `auto_clean_mangle`.
- **email/national-ID → `[PII]`**: `EMAIL_RE` (przez HPLT-spany) + `NATID_RE` (keyword-adjacent PESEL/NIP/REGON/dowód + ≥9-digit).
- `[Telefon]` = **semantic-tag NIE fixed-fake-number** (fake `+48 000...` poisonuje: model memoryzuje high-freq numer; tag = slot-koncept + no-digit → fixpoint convergent).

## phone_scrub v12b — guardy (v6→v12b iteracja, każdy = złapana klasa)
- **label-window 55-char** po phone-labelu (`tel/telefon/kom/kontakt/zadzwoń/dzwoń/infolinia/gsm/fax/faks/nr tel`).
- **`_is_phone`**: 9-11 cyfr; bare = 9 / 10-lead-0 / 11-'48' / 11-'0'-UK; exclude 6+zeros/KRS/DATE/ISBN.
- **account-guard (v10):** skip TYLKO gdy `cluster>11-digit AND account-kw (konto/iban/rachunek/bankverbindung) ≤30-przed-cluster-start` → IBAN(26)+kw skip, genuine-phone(≤11)+konto-obok scrub.
- **separatory `[ \t\-]` nie `\s`** → nie spanuje `\n` (newline-adjacent-list scrubowany osobno).
- **bounded-fixpoint** (cap-8, convergent+guarded — NIE divergentny cascade).

## ⚠️ INVARIANT (FCD-S6): independent-lens, NIE self-report
**Residual-check PII MUSI być independent-lens SZERSZY niż scrub (`check ⊋ scrub`), NIE idempotency (`check == scrub`).** Idem re-runuje ten sam scrub → strukturalnie ślepy na to co scrub SYSTEMATYCZNIE gubi (format-recall-gap). `deep_verify.py` = independent regex+context (date/IBAN/token-excluded). Dowód: idem-residual=12 FALSE-CLEAN vs independent 2377 leak-docs (~1900 real-phone) na tym samym korpusie. Self-report DISQUALIFIED jako clear-signal; 2. arbiter z superset-recall.

## Dedup-vs-base: truncation-variants
Base=truncated-prefix kandydata → **niski Jaccard** (J≈0.2 ≪ 0.8) → MinHash-LSH-0.8 STRUKTURALNIE GUBI (3 vs 3038 na bin9). Łap **prefix-sig-containment** (md5 first-200-char norm) → `--prefix-chars 200`.

## Testy
`tests/test_phone_scrub.py` — acceptance-battery (scrub/keep/leading-0/kom/dzwoń/newline/foreign/IBAN/FP/fixpoint). 8/8 PASS.
