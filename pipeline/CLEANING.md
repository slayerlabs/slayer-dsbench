# CLEANING.md — co pipeline usuwa/naprawia i DLACZEGO

**Cel: ciągłość know-how.** Rejestr KAŻDEJ klasy artefaktu którą `pipeline/` (clean_hplt_v3 + polish_dataset + near_dup) usuwa, naprawia lub świadomie ZOSTAWIA — z uzasadnieniem, FP-safety i zmierzoną skalą. Żeby przyszły maintainer wiedział CO i CZEMU, i żeby nie zgubić decyzji przy skali.

**Metoda (wszystkie fixy):** mierz-nie-zakładaj (skala z bajtów PRZED fixem), FP-safe (0-trafień-na-czystej-prozie przed gate, FP-test przed ship), recoverable>drop gdy się da, accept-gdy-FP-ryzyko>wartość. Dwuwarstwa: hard-scrub at-source + HF-clearance-gate backstop.

---

## 1. DROP — całe dokumenty usunięte

| klasa | co | próg / sygnał | uzasadnienie |
|---|---|---|---|
| lang | nie-`pol_Latn` (pole `lang[0]`) | HPLT lang-id | tylko polski |
| MT-prob | machine-translation ≥ próg | `MT` ≥ 0.20 | MT-slop degraduje |
| register | nie-whitelist rejestr | HPLT register-labels | proza/wiedza, nie spam |
| length | za krótkie / za długie | <400 lub >120k znaków | fragmenty / śmieci |
| boilerplate-frac | zbyt dużo HPLT-PII-spanów | frac > max_frac | dokument-śmieć |
| adult / domain-exclude | adult + blacklist domen | HPLT flags + lista | higiena |
| domain-cap | >N docs z jednej domeny | `max_per_domain` (default 250, diversity-run 50) | różnorodność, anty-mono |
| mojibake-drop | ≥3 CJK/fullwidth/U+FFFD w pierwszych 3000 | `MOJIBAKE_RE` | full-mis-decode |
| **heavily-garbled** | ±-po-małej-literze / ¶¹¬-letter-adj / ³¼¿-w-klastrze-mojibake | `GARBLED` regex | full-mis-decode (nie pojedynczy legit) — FP-safe, 96 docs |
| short-po-polish | <200 znaków PO polish | len | po stripach za mało treści |
| **base-duplicate** | shard ≥99% w bazie dynaword | exact-prefix vs baza (Mierniczy) | redundantny (10_1 tier-10 = base-sample) |

## 2. SCRUB — PII zredagowane in-place (`[PII]`, dokument zostaje)

| klasa | wzorzec | FP-safety |
|---|---|---|
| email | `EMAIL_RE` | standard |
| phone (+48) | `PHONE_RE` = `+`-anchored | 0-trafień na prozie (wymaga `+`) |
| **phone (labeled)** | `PHONE_LABEL_RE`: `\b(tel\|telefon\|kom\|viber\|whatsapp\|fax\|gsm\|nr tel\|numer telefonu)\b` + 8-15 digit | word-boundary (nie hotel/komputer); bare-num-bez-label → clearance. **2096 real-leaków** złapane |
| **national-ID** | `NATID_RE`: `(PESEL\|NIP\|REGON\|dowód osobisty)` + przylegający 9-13 digit | label-adjacent (kontekstowe „podaj PESEL" bez numeru nietknięte); RODO-uniform |
| PESEL bare-11 | 11-cyfr checksum+data-valid | **WARN+surface→clearance** (przykłady/test-data „Przykład: 80100919512" ≠ real PII); tylko keyword-adjacent = hard-error |

## 3. STRIP — fragment usunięty (dokument zostaje)

| klasa | co | FP-safety |
|---|---|---|
| Strona-header | leading „Strona X z Y" | tylko leading match |
| block-frame boilerplate | ciągłe runy ≥MINRUN wysoko-doc-freq linii (menu/nav) | izolowane high-freq (Pozdrawiam) zostają |
| leading-nav-list | leading ≥5 bullet-linii | tylko startowe |
| leading bare-dash | startowe linie = sam myślnik | separator, nie dialog |
| U+FFFD | replacement-char (decode-junk) | zawsze junk |
| intra-word `?` | lowercase-PL `?` lowercase-PL, nie-URL | diacritic-loss ż→? |
| **button-block** | leading button/link-blok (`kliknij\|zaloguj\|zobacz` ≥3 lub ` - `+≥2) + template-headery | region MUSI mieć button-line, stop na realnym zdaniu; **1283 docs, FP=0** |

## 4. REMAP / RECOVER — mojibake naprawione in-place (recoverable>drop)

| klasa | mapowanie | FP-safety |
|---|---|---|
| **Latin-2 mid-word** | `¶±³¼¿` → `śąłźż` (litera-obie-strony) | odróżnia „materia³" od legit „m³"/„5±2" |
| **UTF8-double-encode** | cp1252→utf-8: `Ä…`→ą, `Ä™`→ę, `Å¼`→ż… (lowercase-map) | bare `Å`(Åmål)/`Ã`(São) NIE ruszane |

## 5. ACCEPT — świadomie NIE usuwane → HF-clearance-gate (backstop)

| klasa | dlaczego nie-fix | gdzie |
|---|---|---|
| bare-contextless phone | brak labelu = ambiguous (ID/data/kod) — scrub=over-redakcja | clearance surface |
| bare-11-PESEL-alone | przykład/koincydencja bez label-kontekstu | clearance surface |
| lone `³/¼/¿` | „m³"(legit) ≡ „materia³"(garbled) lokalnie nieodróżnialne | clearance (0.06%) |
| truncation (leading ucięte słowo) | detekcja FP-prone (wiele docs legit-zaczyna różnie); rzadkie | ACCEPT |
| obce diakrytyki (ä/ê/æ/ñ, ää-Pääbo) | legit fińsko/nordyckie/hiszp | NIE mojibake |

---

## Prowenancja findingów
FCD-review Arka (Strona/?/button/truncation) · Wartownik QA (PII-residual/Latin-2/phone-leak/artifacts-check) · Mierniczy census (net-new-vs-baza/garbled-density/utf8/PESEL-example) · Latarnik safety (NATID-RODO-uniform/clearance-gate). PR #3 (pii+neardup+pipeline+artifacts), #4 (phone-labeled), #5 (button+utf8).
