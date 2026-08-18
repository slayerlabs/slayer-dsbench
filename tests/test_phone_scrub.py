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


def test_v14_foreign_and_ext_scrubbed():
    # v14 (Wartownik): foreign-12-digit-structured (bez +) + landline+ext /26
    for s in ["Fax: (49) 7561 91 32 09 biuro", "tel. (022) 208 28 28/26 czynne"]:
        out, n = _fix(s)
        assert n >= 1 and "[Telefon]" in out, (s, out)


def test_v14_newline_wrapped_scrubbed():
    # v14 \n-join: numer zawiniety przez pojedynczy \n (pre-\n <9 cyfr)
    out, n = _fix("telefonu: 0845 302\n1444.")
    assert n == 1 and "[Telefon]" in out, out


def test_v14_currency_kept():
    # v14 CURR-guard: liczba(9+cyfr)+waluta/jednostka = cena/miara, nie telefon -> KEEP
    for s in ["kontakt cena 123 456 789 zl netto", "tel oferta 500 100 200 pln brutto"]:
        out, n = _fix(s)
        assert n == 0, (s, out)


def test_v15_realleaks_scrubbed():
    # v15 (Wartownik 8_5 719-leak): foreign-paren, +spacja, label-po-numerze, distance>55
    for s in ["Telefon: (0044) 161 24 54 130 konsulat", "Prospect ( 847) 870 56 56 tel",
              "Anna Raszewska (690 88 99 22) tel", "telefoniczny Kolodziejczak 728461533 lub"]:
        out, n = _fix(s)
        assert n >= 1 and "[Telefon]" in out, (s, out)


def test_v15_fp_kept():
    # v15 FP-guard: szersze okno/paren NIE lapie faktury/godzin/count przy tel-labelu
    for s in ["faktura 4567 dnia tel biuro", "zamowienie 12345 sztuk tel dzial",
              "tel godz 8 00 do 16 00 czynne", "Tel KRS: 0000245014 XIII"]:
        out, n = _fix(s)
        assert n == 0, (s, out)


def test_v16_paren_newline_and_godz_scrubbed():
    # v16 (Wartownik 8_5 re-run): \n w/po nawiasie + godz-CURR-FP (telefon przed godzinami)
    for s in ["Numer telefonu: (56) 683\n70 67 biuro", "tel. (022)\n5979663 czynne",
              "tel. 84 66 30 247 godz. 7.30-15.30"]:
        out, n = _fix(s)
        assert n >= 1 and "[Telefon]" in out, (s, out)


def test_v16_no_mangle_coords_isbn_timestamp():
    # v16 anti-mangle (digit-anchor): NIE scrubuj cyfr wewnatrz wspolrzednych/ISBN/timestamp przy tel-labelu
    for s in ["wspolrzedne tel 52.1234567890 N szer", "ISBN tel. 9788301123456 ksiazka",
              "czas kontakt 12.12.2024 14:30:00 start", "dane kontaktowe wsp 21.123456 51.98765"]:
        out, n = _fix(s)
        assert n == 0 and "[Telefon]" not in out, (s, out)


def test_v16_1_dot_adjacent_phone_scrubbed():
    # v16.1 (Wartownik 14208-leak regresja): telefon po/przed kropka (zdanie/skrot) MUSI scrub;
    # anchor rozroznia litera.cyfra (telefon) od cyfra.cyfra (decimal/coord)
    for s in ["kontakt.601 234 567 x", "tel 601 234 567. Zadzwon jutro", "dane.tel 501 234 567 biuro"]:
        out, n = _fix(s)
        assert n >= 1 and "[Telefon]" in out, (s, out)


def test_v16_1_decimal_coord_kept():
    # v16.1: cyfra.cyfra (wspolrzedne/decimal) NIE scrub mimo tel-labela
    for s in ["wsp tel 52.1234567890 N", "geo kontakt 21.123456 51.98765"]:
        out, n = _fix(s)
        assert n == 0, (s, out)


def test_v17_foreign_14digit_landline():
    # v17 (Wartownik b125): niemiecki landline 14-cyfr structured -> scrub (maxlen 13->15)
    out, n = _fix("tel. 03591/5251-68000 x")
    assert n >= 1 and "[Telefon]" in out, out


def test_v17_dual_slash_numbers():
    # v17 (Wartownik b125): dwa numery sklejone '/' -> slash-split, oba scrubowane
    out, n = _fix("tel. 56 641 4510/56 641 4376.")
    assert n >= 1 and "[Telefon]" in out and "641" not in out, out


def test_v17_foreign_no_new_mangle():
    # v17 anti-mangle: maxlen 15 NIE lamie coord/NRB/ISBN (cluster-guard >=16 + digit-anchor + _ISBN)
    for s in ["wsp 52.1234567890 N", "IBAN 61 1090 1014 0000 0712 1981 2874", "ISBN 9788301123456"]:
        out, n = _fix(s)
        assert n == 0 and not _mangled(out), (s, out)


def test_v18_number_before_dotted_date():
    # v18 (Wartownik b2): numer przed data-kropkowa "91 449-55-23.13.01.2023" = telefon+data -> scrub numer
    out, n = _fix("telefon 91 449-55-23.13.01.2023 rok")
    assert n >= 1 and "[Telefon]" in out and "449" not in out, (out, n)


def test_v18_two_numbers_adjacent_parens():
    # v18 (Wartownik b2): dwa numery w nawiasach obok "(46) 855 32 42(46) 855 38 13" -> oba scrub
    out, n = _fix("Tel./fax: (46) 855 32 42(46) 855 38 13")
    assert n >= 1 and "855" not in out, (out, n)


def test_v18_two_numbers_space_slash():
    # v18 (Wartownik b2): numer + spacja + drugi-ze-slashem "601-462-038 17/864-22-09" -> oba scrub
    out, n = _fix("Tel: 601-462-038 17/864-22-09")
    assert n >= 1 and "462" not in out and "864" not in out, (out, n)


def test_v18_nrb_bare_spaces_kept_no_multisplit():
    # v18 regresja-guard: 26-cyfr NRB same-spacje przy labelu NIE moze byc multi-splitowany na telefony
    out, n = _fix("kontaktu telefonicznego i internetowego.57 1020 1127 0000 1402 0010 2475")
    assert n == 0, (out, n)


def test_v19_space_merge_two_numbers():
    # v19 (Wartownik b2): dwa numery rozdzielone SPACJA (bez -/) "750 52 82 0660399142" -> mobile scrub
    # (cluster-guard 16->24: dwa telefony 17-22cyfr bez ACCT nie sa blokowane jak NRB)
    out, n = _fix("tel/fax 750 52 82 0660399142 x")
    assert n >= 1 and "0660399142" not in out, (out, n)


def test_v19_nrb_still_kept_after_threshold_raise():
    # v19 regresja: NRB-26 same-spacje przy labelu NADAL kept (cluster>=24 blokuje) mimo podniesienia progu
    out, n = _fix("kontaktu telefonicznego i internetowego.57 1020 1127 0000 1402 0010 2475")
    assert n == 0, (out, n)


def test_v19_card16_kept():
    # v19 regresja: karta-16 przy tel NIE scrub (cluster<24 ale _is_phone odrzuca 16>15 struct)
    out, n = _fix("tel karta 1234 5678 9012 3456 platnosc")
    assert n == 0, (out, n)


def test_v20_dash_spacing_pl():
    # v20 (Wartownik b2): spacja-wokol-myslnika "504 - 729 098", "81- 752-00-22" -> scrub (separator {0,3})
    for s in ["obiadow tel 504 - 729 098 x", "tel 81- 752-00-22 biuro", "kontakt (25) 792 -42- 51 x"]:
        out, n = _fix(s)
        assert n >= 1 and "[Telefon]" in out, (s, out)


def test_v20_dashed_intl():
    # v20: intl caly przez myslniki "00-33-07-63-32-49-26" -> scrub (separator-flex lapie)
    out, n = _fix("tel 00-33-07-63-32-49-26 FR")
    assert n >= 1, (out, n)


def test_v20_no_regression_coord_date_hours():
    # v20 anti-mangle: separator-flex NIE lapie coord/data-spaced/godzin (bez kropki, guardy trzymaja)
    for s in ["wsp 52.1234567890 N", "data 2020 - 01 - 15 rok", "godziny 900 - 1700 otwarte", "wsp 52 - 21 - 1234567 N"]:
        out, n = _fix(s)
        assert n == 0, (s, out)
