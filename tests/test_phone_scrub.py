"""Testy phone_scrub v12b (label-window PII phone-scrub -> [Telefon]).

Broni obserwowalnego kontraktu: real-phone SCRUB, non-phone (IBAN/date/count/invoice-16) KEEP,
FP-safe labels (kombinat/komora), bounded-fixpoint convergent. Bateria = klasy złapane v6->v12b.
"""
from __future__ import annotations
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import phone_scrub as P  # noqa: E402


def _fix(text, cap=8):
    """bounded-fixpoint (jak w clean_hplt_v3): scrubuj do zbieżności."""
    total = 0
    for _ in range(cap):
        text, n = P.scrub_phones_labelwindow(text)
        total += n
        if n == 0:
            break
    return text, total


def _mangled(text):
    return bool(re.search(r"\[Telefon\][-\d]", text))


IBAN = "26 1140 2004 0000 3002 0135 5387"


def test_labeled_phones_scrubbed():
    for s in ["tel. 22-266-86-18 biuro", "kontakt 601 983 672 x",
              "infolinia 800 123 456", "dzwoń 608837979 w sprawie",
              "kom. 501 234 567", "zadzwoń pod nr tel.: 12 345 67 89"]:
        out, n = _fix(s)
        assert n >= 1 and "[Telefon]" in out, (s, out)
        assert not _mangled(out), out


def test_leading_zero_landline():
    # 0-prefix trunk / bare-10-leading-0 (v8/v11)
    for s in ["tel 076 85-82-397 x", "tel. 0-91 449 4690", "tel. 0227382320 czynne"]:
        out, n = _fix(s)
        assert n == 1 and "[Telefon]" in out and not _mangled(out), (s, out)


def test_foreign_uk_bare_scrubbed():
    # RODO-scope: foreign labeled phones (v12b)
    for s in ["tel. 07531442627 UK", "Tel. 02078228900 London"]:
        out, n = _fix(s)
        assert n == 1 and "[Telefon]" in out, (s, out)


def test_newline_adjacent_list_both_scrubbed():
    # v12b: separatory [ \t\-] nie \s -> nie spanuje \n -> lista rozdzielona
    out, n = _fix("tel. 510 459 229\n556 208 305 czynne")
    assert n == 2 and out.count("[Telefon]") == 2, out


def test_iban_account_kept_no_mangle():
    # cluster>11 + account-kw -> skip (v7/v9/v10); brak partial-scrub mangle
    for s in ["NR KONTA BS: kontaktowy " + IBAN,
              "Bankverbindung: kontakt PL " + IBAN,
              "kontakt Konto Santander: " + IBAN]:
        out, n = _fix(s)
        assert n == 0 and not _mangled(out), (s, out)


def test_genuine_phone_after_account_word_scrubbed():
    # v10: genuine-phone (<=11) + konto/rachunek-obok -> SCRUB (nie over-skip-leak)
    for s in ["konto firmowe. Telefon: 601 234 567", "rachunek 12 3456, tel 502 111 222"]:
        out, n = _fix(s)
        assert n == 1 and "[Telefon]" in out, (s, out)


def test_non_phone_kept():
    # FP-safe: date / long-count / invoice-16-digit / kombinat-komora (kom-label FP) / no-label
    for s in ["wydarzenie 2009-01-22 godz 14", "kombinat produkcyjny 123456789 ton",
              "w komorze 12345678 stopni", "faktura 1234 5678 9012 3456 zapłać",
              "numer klienta 123456789012 w systemie"]:
        out, n = _fix(s)
        assert n == 0, (s, out)


def test_fixpoint_convergent():
    # bounded-fixpoint zbiega (pass po _fix scrubuje 0)
    out, _ = _fix("pod nr tel.: 12 345 67 89, 98 765 43 21, 77 45 11 928, 22 111 22 33")
    _, again = P.scrub_phones_labelwindow(out)
    assert again == 0, out


def test_labeled_bare10_scrubbed():
    # v13 (Wartownik recall-gap): labeled bare-10 non-leading-0 = real phone -> scrub (RODO safe-superset)
    for s in ["Jej telefon: 9006121511", "numer tel 9006121511 do mnie", "kontakt 9006121511"]:
        out, n = _fix(s)
        assert n == 1 and "[Telefon]" in out, (s, out)


def test_nrb_near_label_kept():
    # v13.1 (Wartownik NRB-edge): 26-digit NRB near "kontaktu" label -> KEEP (>=16-digit cluster = account, nie telefon)
    for s in ["kontaktu telefonicznego i internetowego.57 1020 1127 0000 1402 0010 2475",
              "kontakt: 1020 1127 0000 1402 0010 2475 nr rachunku"]:
        out, n = _fix(s)
        assert n == 0 and not _mangled(out), (s, out)
