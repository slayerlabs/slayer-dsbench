# SOTA data-cleaning dla pretreningu LLM — research + gap-analiza (dsbench)

> Autor: Monter (N-03), 2026-08-11. Odpowiedź na prośbę Arka ("research jak to powinno wyglądać + nasze dokumenty").
> Cel: porównać nasz stack (`slayer-dsbench` + pipeline) z open-corpus SOTA, znaleźć tanie+wartościowe luki dla pętli uczącej (kolejne modele GoLLeM).

## 1. SOTA pipelines (co robią, kolejność, ablacja)

| Pipeline | Filtry (kolejność) | Dedup | Quality | Ablacja-insight |
|---|---|---|---|---|
| **FineWeb** (HF, 15T) | lang(fastText) → Gopher rep+quality → C4 (bez terminal-punct — za agresywny) → +3 własne (dup-line frac, short-line frac, terminal-punct) | **MinHash 5-gram @75% PER-SNAPSHOT** (NIE global — global usuwa starszą wysokojakościową treść, robi distribution-shift) | heurystyki | 3 top filtry = ~22% tok out; **FineWeb-Edu (klasyfikator edu z anotacji Llama-3-70B) = największy win: MMLU 33%→37%, 1.3T bije surowe 15T @ fixed-compute** |
| **Dolma** (AI2, 3T) | lang-ID → quality(C4+Gopher heurystyki, ŚWIADOMIE nie model-based, repro) → dedup → content | 2-stage: URL-dedup + paragraph-dedup (Bloom filter) | heurystyki + toxicity(FastText Jigsaw: hate/NSFW) | PII: regex email/IP/telefon, mask ≤5 spanów/dok special-token |
| **Gopher** (MassiveText) | SafeSearch → 11 quality rules → repetition | MinHash | heurystyki | 11 rules: word-count 50-100k, avg-word-len 2-10, symbol/word <0.1, ≥80% słów z literą, <90% linii-bulletów, <30% linii-ellipsis, n-gram repetition (2gram char-frac<0.20 ... 10gram<0.10), dup-linie/paragrafy <30% |

Źródła: FineWeb arXiv:2406.17557 · Dolma arXiv:2402.00159 · Gopher (MassiveText) via FineWeb/Dolma reimpl.

## 2. Co MAMY (dsbench + pipeline) — reuse, nie reinwencja

- **dsbench checks:** license (SPDX/open-gate) · pii (PESEL checksum/NIP/REGON/email/telefon) · dedup (exact) · neardup (MinHash+LSH) · decontam (eval-set overlap) · **boilerplate (NOWY: web-comment-cruft HARD/SOFT + span-strip)** · empty · integrity (sha256) · stats.
- **pipeline:** clean_hplt_v3 (lang-prob, MT-ratio, register-allowlist ID/OP/HI/IN/NA, len, boilerplate-regex, adult-spam, mojibake, domain-exclude, PII-scrub) · polish_dataset (frame_merge block-dedup ≥3-linii, nav-strip) · near_dup_vs_dynaword.

**Pokrycie vs SOTA:** mamy lang, PII (mocniej niż Dolma — checksum PESEL/NATID), dedup exact+near, register-filter (~ proxy quality), boilerplate. Kolejność ~zgodna (clean→dedup→bramka).

## 3. GAP-ANALIZA (priorytet: tani+wartościowy first)

1. **[TANIE, wysoki] Gopher-heurystyki jako dsbench check** (`checks/quality_heuristics.py`): symbol/word-ratio, alfabet-char-frac, bullet/ellipsis-line-frac, avg-word-len, word-count-bounds, n-gram-repetition-frac. Mamy część (register/len w clean_hplt_v3) ale NIE jako mierzalna bramka. FP-safe, deterministyczne. **Dodać.**
2. **[DROGIE, NAJWYŻSZY dla NAS] Quality-classifier (FineWeb-Edu style).** To był największy win FineWeb (bije więcej-surowych-tokenów). Nasz problem = FAKTY słabe + HPLT boilerplate-scrubbed ale NIE quality/edu-classified (Latarnik R2). **Edu/quality-scorer na HPLT (anotacje z naszego GoLLeM albo zewn. LLM → mały klasyfikator) = następna duża dźwignia faktów.** Kandydat na dedykowany run pętli.
3. **[TANIE, śr.] Dedup-scope discipline:** FineWeb dowiódł per-source/snapshot > global (global robi distribution-shift, wycina starą wysokojakościową treść). Nasz neardup — świadomie per-source, nie cross-corpus bez powodu.
4. **[TANIE, śr.] FineWeb top-3 heurystyki** (dup-line-frac, short-line-frac, terminal-punct-frac) — mamy część via frame_merge; sformalizować jako check z progami z ablacji.
5. **[ŚR, niski dla PL-CC0] Toxicity-classifier** (Dolma FastText) — mamy adult-spam-regex; classifier lepszy, ale nasz korpus CC0-curated = niższe ryzyko. Później.

## 4. Rekomendacja dla pętli
Kolejny model: dodać **(1) Gopher-heurystyki** (tanie, od razu do dsbench) + rozważyć **(2) quality-classifier na HPLT** jako dedykowany eksperyment (mierzalny cel: fakty↑ na held-out). To zamienia "boilerplate-scrub" w pełną **quality-curation** — dokładnie to co odróżnia FineWeb-Edu od surowego web.
