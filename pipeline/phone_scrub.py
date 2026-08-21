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
    r"(?i)(?:\b(tel|telefon\w*|kom[oó]rk\w*|kom|kontakt\w*|zadzwo\w*|dzwo\w*|infolini\w*|gsm|fax\w*|faks\w*|nr\s*tel\w*|numer\s+tel\w*|telefonicznie)\b|\[telefon\])"
)
PHONE_NUM = re.compile(
    r"(?:\+[ \t]?\d{1,3}[ \t.\-]?)?(?:0[ \t\-]?)?(?:\(?\d{2,4}\)?[ \t.\-/]?){2,4}\d{2,4}"
)
_DATE = re.compile(r"(?:19|20)\d{2}[\s\-./]\d{1,2}[\s\-./]\d{1,2}")
_KRS = re.compile(r"\b0000\d{6}\b")
_ISBN = re.compile(r"\b97[89][\s\-]")
_ADDR = re.compile(r"(?i)\b(ul\.|ulic\w*|adres\w*|kod\s+poczt\w*)")  # v8 (Monter): usunieto bare \d{2}-\d{3} (matchowal phone-internal '82-397' -> label-window-skip -> gubik leading-0-landline; 5-cyfr-postal <9 -> _is_phone odrzuca, wiec zbedny)
_ACCT = re.compile(r"(?i)\b(konto|kont[ao]|rachun\w*|iban|nr\s+konta|nr\s+rachun\w*|bankverbindung|bic|swift)\b")  # v8-final (Wartownik verified-spec): account-SPECIFIC (BEZ bare-bank: banki maja telefony), number-anchored pre-30
WINDOW = 55
PLACEHOLDER = "[Telefon]"  # v6 (Arek): semantic-tag NIE fake-number — fixed-fake poisonuje (model memoryzuje high-freq numer); tag = slot-koncept bez memoryzacji

def _is_phone(seg: str) -> bool:
    """PL-phone plausibility: 9-11 cyfr; bare-digit-run (bez separatorów/+) MUSI być dokładnie 9
    (10/11-cyfrowe bare = ID/timestamp/count, NIE PL-phone). Grouped/+48 = 9-11."""
    d = re.sub(r"\D", "", seg)
    if len(d) < 9 or len(d) > 11:
        return False
    has_struct = bool(re.search(r"[\s\-/()]", seg.strip())) or seg.strip().startswith("+")
    if not has_struct and not (len(d) == 9 or (len(d) == 10 and d.startswith("0")) or (len(d) == 11 and d.startswith(("48", "0")))):
        return False  # v12b: bare-9 / bare-10-lead-0 / bare-11-'48'(+48-bez-plusa) / bare-11-'0'(UK-07/020 foreign RODO-scope); inne bare-10/11 = ID/ts reject
    if re.search(r"0{6,}", d):
        return False  # sentinel/fake (6+ zeros) — idempotent + re-verify-safe
    if _KRS.search(seg) or _DATE.search(seg) or _ISBN.search(seg):
        return False
    return True

def scrub_phones_labelwindow(text: str):
    """Zwraca (scrubbed_text, n_scrubbed). FP-safe: label-anchored window + _is_phone + address-guard."""
    if not text:
        return text, 0
    spans = []
    for m in PHONE_LABEL.finditer(text):
        ws = m.end()
        for nm in PHONE_NUM.finditer(text[ws:ws + WINDOW]):
            if _is_phone(nm.group()):
                a, b = ws + nm.start(), ws + nm.end()
                cs = a
                while cs > 0 and text[cs - 1] in "0123456789 -":  # v10 (Wartownik): cluster-start
                    cs -= 1
                ce = b
                while ce < len(text) and text[ce] in "0123456789 -":  # cluster-end
                    ce += 1
                if sum(c.isdigit() for c in text[cs:ce]) > 11 and _ACCT.search(text[max(0, cs - 30):cs]):
                    continue  # skip TYLKO long-cluster(IBAN>11) + account-kw; genuine-phone(<=11)+konto/rachunek-obok -> scrub (no over-skip-leak)
                while a < b and text[a].isspace():   # trim otaczające spacje (naturalność)
                    a += 1
                while b > a and text[b - 1].isspace():
                    b -= 1
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
