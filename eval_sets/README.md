# eval_sets

Dane pomocnicze bramki i klasyfikatora rejestrów: hashe do dekontaminacji, próbki z etykietami rejestru oraz wyniki pomiarów (`*.json`).

## Pliki z tekstem źródłowym

`hplt-register-silver-v0.jsonl`, `hplt-register-silver-v1.jsonl`, `human-gold-review.jsonl`, `human-review-partia-02.jsonl`, `human-review-partia-03.jsonl`, `register-gold-partia-04.jsonl` oraz `datasets/hplt-registers-example/sample.jsonl` zawierają fragmenty polskich stron WWW z korpusu [HPLT v3](https://huggingface.co/datasets/HPLT/HPLT3.0), z etykietami rejestru nadanymi automatycznie lub ręcznie.

- **Licencja:** HPLT udostępnia opakowanie danych na licencji CC0-1.0. Prawa do samych tekstów mają autorzy stron. Teksty służą tu wyłącznie do oceny klasyfikatora rejestrów (eksploracja tekstów i danych, art. 4 dyrektywy 2019/790).
- **Dane osobowe:** przed publikacją wszystkie pliki przeszły skan danych osobowych (adresy e-mail, telefony, PESEL, NIP, REGON, dowód osobisty, IBAN, numery kart, adresy IP); wynik: 0 trafień.
- **Usunięcie:** jeśli fragment narusza Twoje prawa albo zawiera Twoje dane, zgłoś to w issue tego repozytorium, podając plik i `id` rekordu. Rekord usuniemy. Usunięcie u źródła: [polityka HPLT](https://huggingface.co/datasets/HPLT/HPLT3.0#terms-of-use-and-takedown).

## Pozostałe pliki

| plik | zawartość |
|---|---|
| `hashes.txt` | hashe tekstów zbiorów ewaluacyjnych do `checks/decontam.py` |
| `logreg_coef.npz` | współczynniki regresji logistycznej klasyfikatora rejestrów (`coef`, `intercept`, `classes`); bez tekstu, wczytywany z `allow_pickle=False` |
| `baseline-register-tfidf.json`, `embed-register-e5.json`, `calibrate-register-e5.json` | wyniki klasyfikatora: baseline TF-IDF, e5 + regresja logistyczna, progi pewności per rejestr |
| `glimmer-vs-opus.json`, `garbage-rules-scan*.json` | zgodność etykietowania i skany reguł śmieci na próbce web |
