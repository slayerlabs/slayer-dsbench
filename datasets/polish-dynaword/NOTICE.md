# NOTICE — atrybucja dla `sample.jsonl`

`sample.jsonl` to **realny, przycięty podgląd** korpusu
[SlayerLab/polish-dynaword](https://huggingface.co/datasets/SlayerLab/polish-dynaword)
(v0.2.1): po 3 rekordy z każdego z 12 źródeł, `text` przycięty do ~1200 znaków,
zachowane pola `id, text, source, license, author`. Służy CI dsbench jako fixture
audytujący **realne** dane (nie syntetyk).

- **Licencja podglądu:** CC-BY-SA-4.0 (jak korpus źródłowy; share-alike).
- **Atrybucja:** teksty pochodzą z otwartych korpusów (EUR-Lex, Polski Korpus
  Parlamentarny, Wikipedia/Wikisource/Wikiquote/Wikivoyage/Wikibooks/Wikinews,
  Wolne Lektury, 1000 Novels Corpus CLARIN-PL, ELTeC-pol, Dziennik Ustaw),
  redystrybuowanych przez **SpeakLeash** i skurowanych w **polish-dynaword**
  (Kacper Wikieł, Bart Kobyliński). Prawa przy oryginalnych autorach/źródłach.
- Licencja per-źródło: patrz `sources.yaml` oraz karta datasetu (tabela „Sources").
- Usunięcie treści: `k.wikiel@gmail.com` (polityka notice-and-takedown dynaworda).
