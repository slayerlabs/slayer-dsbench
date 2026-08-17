"""
phone_scrub_labelwindow v4 — FP-validated extended phone-scrub (Latarnik, 2026-08-07).
Label-block-window: scrub phone-format w oknie WINDOW po phone-labelu. Zamyka recall-gap
(paren/compound/zadzwoń/infolinia/kontakt/dash-landline/2.-w-liście) BEZ over-scrub.

ITERACJE (own-errors → FCD-R4):
 v1 recall 97-99%; v2 +kontakt(address-guard); v3 postal-guard-lookahead (dash-landline);
 v4 bare-run-tylko-9-cyfr (over-scrub fix: 10/11-cyfrowe bare ID/timestamp/count przy labelu
    NIE są PL-phone → KEEP; PL-phone bare=9, +48=11, grouped=9-11).
 v7 (Monter-finding batch-5_1): cluster-digit-guard — skip kandydata jesli otaczajacy digit-cluster
    >11 cyfr (26-cyfrowy IBAN/konto near 'kontakt'-label -> partial-scrub pierwszych 9-11 = mangling).
LEKCJA: FP-test MUSI być na REPREZENTATYWNych danych (web: counts/msg-ID/timestamp),
 nie tylko czystej prozie literackiej (wolne_lektury nie miało tych confounderów → v1-3 przepuściły).

FP-validated (FCD-R3, 0-PRZED-gate): wolne_lektury=0; confounders (10-digit-count/unix-ts przy tel)=KEEP;
address „Adres kontaktowy 80-339"/postal=KEEP; ISBN/KRS/DATE=KEEP. Recall: paren/compound/dash/2nd=SCRUB.
IDEMPOTENT (pass2-additional=0 na 6_2 — bezpieczny multi-pass, ale i tak: aplikuj RAZ/regenerate).
⚠️ Invariant (Wartownik check≥scrub): residual-check MUSI używać TEJ funkcji.
"""
import re

PHONE_LABEL = re.compile(
    r"(?i)\b(tel|telefon\w*|kom[oó]rk\w*|kom|kontakt\w*|zadzwo\w*|dzwo\w*|infolini\w*|gsm|fax\w*|faks\w*|nr\s*tel\w*|numer\s+tel\w*|telefonicznie)\b"  # v11: +dzwo\w* (dzwoń-family, Wartownik deep-verify recall-gap)
)
PHONE_NUM = re.compile(
    # v15: opcjonalny foreign country-code w nawiasach "(0044)"/"( 847)"/"(+44)" PRZED zwyklym wzorcem
    # v16: digit-anchor (?<![\d.]) / (?![\d.]) = nie zaczynaj/koncz w srodku ciagu cyfr (anty-mangle: wspolrzedne 21.123..., timestamp, ISBN)
    r"(?<![\d.])(?:\(\s?\+?0{0,2}\d{1,4}\s?\)[ \t\-]?)?\(?(?:\+?[ \t]?48[ \t\-]?)?(?:0[ \t\-]?)?(?:\(?\d{2,4}\)?[ \t\-/]?){2,4}\d{2,4}(?![\d.])"
)
_DATE = re.compile(r"(?:19|20)\d{2}[\s\-./]\d{1,2}[\s\-./]\d{1,2}")
_KRS = re.compile(r"\b0000\d{6}\b")
_ISBN = re.compile(r"\b97[89][\s\-]")
_ADDR = re.compile(r"(?i)\b(ul\.|ulic\w*|adres\w*|kod\s+poczt\w*)")  # v8 (Monter): usunieto bare \d{2}-\d{3} (matchowal phone-internal '82-397' -> label-window-skip -> gubik leading-0-landline; 5-cyfr-postal <9 -> _is_phone odrzuca, wiec zbedny)
_ACCT = re.compile(r"(?i)\b(konto|kont[ao]|rachun\w*|iban|nr\s+konta|nr\s+rachun\w*|bankverbindung|bic|swift)\b")  # v8-final (Wartownik verified-spec): account-SPECIFIC (BEZ bare-bank: banki maja telefony), number-anchored pre-30
_CURR = re.compile(r"(?i)^\s{0,3}(z[lł]|pln|eur|usd|gbp|%)\b|^\s{0,2}[€$£]")  # v16: TYLKO waluta (usunieto godz/km/kg/szt/ton/mln - "godz" zjadalo telefon przed godzinami otwarcia, Wartownik)
WINDOW = 75  # v15: 55->75 (Wartownik 8_5: numer 56-70 zn od labela / po newline+nazwisko przeciekał)
PLACEHOLDER = "[Telefon]"  # v6 (Arek): semantic-tag NIE fake-number — fixed-fake poisonuje (model memoryzuje high-freq numer); tag = slot-koncept bez memoryzacji

def _is_phone(seg: str) -> bool:
    """PL/foreign-phone plausibility. WYLACZNIE label-anchored (po PHONE_LABEL) -> label = mocny dowod."""
    d = re.sub(r"\D", "", seg)
    has_struct = bool(re.search(r"[\s\-/()]", seg.strip())) or seg.strip().startswith("+")
    core = d[2:] if d.startswith("00") else d  # v15: strip intl-prefix "00" (foreign "(0044) 161..." = 14 cyfr surowych, 12 znaczacych)
    # v14 (Wartownik foreign-12/ext): structured (separatory/+) do 13 cyfr (foreign country-code+national,
    # ext '/26'); bare (goly run) do 11 (bare-12/13 = ID). v13: bez bare-length sub-gate (RODO safe-superset).
    if len(core) < 9 or len(core) > (13 if has_struct else 11):
        return False
    if re.search(r"0{6,}", d):
        return False  # sentinel/fake (6+ zeros) — idempotent + re-verify-safe
    if _KRS.search(seg) or _DATE.search(seg) or _ISBN.search(seg):
        return False
    return True

def _passes_guards(text, a, b):
    """Cluster/CURR guardy wspolne dla normal + wrap-match. a,b = span numeru w text.
    NEG-guard (NIP/REGON/PESEL) CELOWO pominiety: NATID_RE lapie je jako [PII], a broad-NEG
    na 'konto' lamie v10 (genuine-phone + konto-obok -> SCRUB). IBAN/NRB/karta -> cluster>=16."""
    cs = a
    while cs > 0 and text[cs - 1] in "0123456789 -":  # cluster-start
        cs -= 1
    ce = b
    while ce < len(text) and text[ce] in "0123456789 -":  # cluster-end
        ce += 1
    cluster_digits = sum(c.isdigit() for c in text[cs:ce])
    if cluster_digits > 13 and (cluster_digits >= 16 or _ACCT.search(text[max(0, cs - 30):cs])):
        return False  # >=16-cyfr cluster (NRB-26/karta-16) LUB >13+account-kw (IBAN near konto) = NIE telefon
    if _CURR.match(text[ce:ce + 6]):
        return False  # v14: liczba+waluta/jednostka (zl/PLN/EUR/%/km) = cena/miara nie telefon (scrub_v38 CURR-guard)
    return True

def scrub_phones_labelwindow(text: str):
    """Zwraca (scrubbed_text, n_scrubbed). FP-safe: label-anchored window + _is_phone + cluster/NEG/CURR-guardy."""
    if not text:
        return text, 0
    spans = []
    for m in PHONE_LABEL.finditer(text):
        ws = m.end()
        win = text[ws:ws + WINDOW]
        for nm in PHONE_NUM.finditer(win):
            if _is_phone(nm.group()):
                a, b = ws + nm.start(), ws + nm.end()
                if not _passes_guards(text, a, b):
                    continue
                while a < b and text[a].isspace():   # trim otaczajace spacje
                    a += 1
                while b > a and text[b - 1].isspace():
                    b -= 1
                spans.append((a, b))
        # v15 bidirectional: numer PRZED labelem ("(690 88 99 22) tel", "( 847) 870 56 56 tel")
        pre_s = max(0, m.start() - WINDOW)
        pcand = list(PHONE_NUM.finditer(text[pre_s:m.start()]))
        if pcand:
            nm = pcand[-1]  # najblizszy labela
            if _is_phone(nm.group()):
                a, b = pre_s + nm.start(), pre_s + nm.end()
                if _passes_guards(text, a, b):
                    while a < b and text[a].isspace():
                        a += 1
                    while b > a and text[b - 1].isspace():
                        b -= 1
                    spans.append((a, b))
        # v14/v16 \n-join: numer zawiniety przez \n (pre-\n <9 cyfr = niepelny). v16: dopusc nawias "(56) 683\n70 67", "(022)\n5979663"
        for wm in re.finditer(r"(\(?\d[\d \t\-()]{0,18})\n([ \t]*\d[\d \t\-()]{0,18}\d)", text[ws:ws + WINDOW + 20]):
            pre_d = sum(c.isdigit() for c in wm.group(1))
            tot_d = pre_d + sum(c.isdigit() for c in wm.group(2))
            if pre_d < 9 and 9 <= tot_d <= 11:
                a, b = ws + wm.start(), ws + wm.end()
                if _passes_guards(text, a, b):
                    spans.append((a, b))
    if not spans:
        return text, 0
    spans.sort()
    merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    out = text
    for a, b in reversed(merged):
        out = out[:a] + PLACEHOLDER + out[b:]
    return out, len(merged)
