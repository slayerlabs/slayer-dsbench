# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, "C:/tmp/dsbench-monter/pipeline")
import deep_verify as dv

FP = {
 "emergency": "TELEFONY ALARMOWE:\n112\n997\n999\nRATOWNICTWO",
 "daty-iso": "numer telefonu zmieniony\n20 kwietnia 2020\n2020-07-10T12:55 aktualizacja",
 "spid": "tel 2360001 SPID1: 32055512380001\nSPID2",
 "username1": "kontaktów brak\nstudent1206\n06-01-2011, 11:30",
 "username2": "kontakt:\nMonika1993\n2014-02-06 11:24\ndalej",
 "username3": "telefony pisał/a:\nJarost1403\n2011-01-01 21:27\nW",
 "wersji": "Kontakty w wersji 3.79.25.482243121 wprowadzono",
 "wersji2": "Kontaktów w wersji 4.22.37.586680692. Teraz",
 "jadro": "w telefonie wersja jądra 3.0.31-1211311\nnumer",
 "krs-spacja": "KONTAKT\nNr KRS: 00000 55578\nNIP:",
 "hotline": "infolinia Zielona Linia - 00800 3428\nVolk",
 "eu-projekt": "Kontakt (HU01-KA220-HED-000086240) został",
 "nrb-fragment": "telefonicznym: 18 2030 [PII]0 0218 5870\nNr S",
 "nrb-fragment2": "Telefon m 52 2030 [PII]0 0016 5330 Dziękuję",
 "polisa": "tel ubezpieczeniowa nr 436000109472\nUrząd",
 "rejestr-tychy": "Telefon Miasta Tychy: 000515922\nUrząd",
 "picker": "telefonów wybierz ilość\n1-10\n11-50\n51-100\n101+",
 "godziny": "tel pn-pt :\nsobota:\n900-1700\n800-1500\nOferta",
 "archiwum": "telefonicznie archiwum wiadomości\n2016\n2015\n2014\n2013",
 "matura": "tel [Telefon].\nMatura 2010\n2010-05-03\nOd 4",
 "artykul": "komórkami: artykuł nr 3517\n2006-10-12 13:49:22",
 "filename": "Telefon img18.us/img18/4996/27042011001.jpg\n",
 "imei": "Telefon MOTOROLA Nr IMEI 359812002840093 wraz",
 "fragment-bare": "kontakt tylko takie tam 61541567415841 komen",
 "bare-0-9d": "Dzwonił numer 004873030 nie jest",
}
REAL = {
 "dot-merge": "tel/fax.750 52 82.0660399142.Smacznego",
 "zero-dot-paren": "tel. domowy (0.59) 84-34-814\nInstytut",
 "zero-dot-paren2": "Kontakt\n- (0.12) 617-20-66\n- [PII]",
 "dashed-intl": "tel [Telefon] lub 00-33-07-63-32-49-26\nWpłaty",
 "spaced-dash": "Tel. (25) 792 -42- 51 zapraszamy",
 "prefix-dash": "telefoniczny [Telefon]\n81- 752-00-22 (Administracja)",
 "dash-space": "tel obiadów: 504 - 729 098 czekamy",
 "landline62": "tel. (62) 749 95 43.2) wtorek",
 "landline32": "tel. (32) 60 32 200.3. Pozdrawiam",
 "uk-mobile": "telefoniczny\nAnia\n07518346235\n£9.5",
 "uk-leeds": "wyborze zadzwnon 0113-820952.",
 "at": "Austria\nTel. 00431 711 32\nFax",
 "warszawa": "kontakt na Niedzielska 0-22 7951021 7899006wew.1",
 "intl-paren": "tel. 00 48 (32) 20 20 100 w. 54",
 "de": "kontakt od nr.telefonu:004906187- 906330 lub [PII]",
}
bad = []
for k, t in FP.items():
    r = dv.independent_leak_scan(t)
    if r: bad.append("FP-NIE-WYKLUCZONY %s: %r" % (k, r))
for k, t in REAL.items():
    r = dv.independent_leak_scan(t)
    if not r: bad.append("REAL-ZGUBIONY %s" % k)
print("\n".join(bad) if bad else "OK: %d FP wykluczone, %d REAL trzymane" % (len(FP), len(REAL)))
