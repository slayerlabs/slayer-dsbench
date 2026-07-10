---
type: reference
id: R1
title: "Inwentarz danych SpeakLeash na dysku + ograniczenia środowiska"
status: aktywny
parents: []
author: Arkadiusz Słota
date: 2026-07-10
created_at: 2026-07-10
---

# R1 — Inwentarz danych SpeakLeash

## Co to / skąd
- **Żywe dane**: `C:/ProjektyPublic/datasets/speakleash-tokenizer-5gb-sample/` — klon HF `kacperwikiel/speakleash-tokenizer-5gb-sample`. Shardy `data/tokenizer_sample_000{1..6}.jsonl.zst`, rekord = `{text, source, source_kind}`. `sample_stats.json`: 1 946 680 doków, 76 źródeł, 5 rodzajów (wiki / prose / academic / forum / web_synt). Shard _0006 = 3 doki (`web_synt_0012`), PII-czyste.
- **polish-dynaword**: `C:/ProjektyPublic/datasets/polish-dynaword/` — tylko blob-parquet per źródło. ZERO kodu (nie repo gita). Skryptu/bramek Bartka TU NIE MA (→ D2).

## Istotne dla nas
- Silnik czyta rekordy `open(utf-8)+json.loads` per linia (`engine.py:load_records`) — **zero obsługi `.zst`**. Podanie `.zst` wprost do `--data` = lawina `__parse_error__`. Dekompresja do plain `.jsonl` OBOWIĄZKOWA.
- `zstd` CLI **nie istnieje** na tym boxie; Python `zstandard` 0.25.0 **jest** → dekompresja tylko Pythonem (streaming: `ZstdDecompressor().stream_reader`).
- `source_files.txt` = te same 76 źródeł co skeleton `sources.yaml`.
- Shardy _0001.._0005 ok. 340–355 MB każdy; _0001 = 442 001 doków, uporządkowane po źródle (pierwsze ok. 249 tys. = plwiki). Multi-źródłowy sampling wymaga stridingu przez cały shard (stąd slice co 200. rekord → 2211 dok. / 6 źródeł).

## Powiązania
[[../INDEX]]
