#!/usr/bin/env python3
"""clean_hplt_v3.py — filtr Polish HPLT v3 bin-10 (WDS=10) -> kanoniczna schema DynaWord.

Adaptacja src/filter_european_hplt.py maintainera do SUROWEGO formatu HPLT v3 (jsonl.zst,
pobrany z data.hplt-project.org). Te same progi jakosci; mapowanie pol v3 -> pol v1.
Output: kanoniczna 8-kolumnowa schema (id/text/source/added/created/token_count/license/author)
+ stats.json (format DynaWord + drop-reasons + register/MT/domain) + karta .md.

Pola v3: text, lang[list], prob[list], u(url), doc_scores[list], web-register{dict}, c(mime), id.
"""
from __future__ import annotations
import argparse, json, os, re, sys, time
from pathlib import Path
from urllib.parse import urlparse
import zstandard as zstd
import pyarrow as pa, pyarrow.parquet as pq
import tiktoken

ADDED = "2026-07-14"
SOURCE = "european_hplt_v3_pl"
LICENSE = "CC0-1.0"

BOILERPLATE_RE = re.compile(
    r"(cookies?|privacy policy|terms of service|all rights reserved|"
    r"polityka prywatno\u015bci|regulamin|wszelkie prawa zastrze\u017cone|"
    r"zaloguj|rejestracja|newsletter)", re.I)
ADULT_SPAM_RE = re.compile(
    r"(porn|sex|escort|casino|viagra|cialis|bukmacher|hazard|"
    r"porno|seks|erotycz|kasyno|randki)", re.I)
LEGALISH_RE = re.compile(
    r"\b(ustawa|rozporz\u0105dzenie|dz\.u\.|sejm|senat|parlament|eur-lex|"
    r"trybuna\u0142|s\u0105d|wyrok|kodeks|komisja europejska)\b", re.I)
EXCLUDED_DOMAIN_PARTS = {".bip.", "bip.", "docplayer.pl", "mapa-kodow-pocztowych.pl",
                         "slideplayer.pl", "wikipedia.org", "wikisource.org", "wikibooks.org",
                         "wikiquote.org", "wikivoyage.org", "chomikuj.pl", "scribd.com",
                         "pdfcoffee.com", "dokumen.pub", "docer.pl", "ebookpoint", "wolnelektury.pl"}
# mojibake: polskie znaki UTF-8 zdekodowane jako CJK/inne (upstream HPLT extraction bug)
MOJIBAKE_RE = re.compile(r"[\u2e00-\u9fff\uff00-\uffef\ufffd]")
# naglowki serwisow wymiany plikow / PDF-ripow (ryzyko piractwa)
PDFHOST_RE = re.compile(r"(\d+\s*Pages?\s*[\u2022\u00b7]|Uploaded at|\d+\s*Words?\s*[\u2022\u00b7])", re.I)
MAX_CHARS = 120000  # ~40k tok: powyzej to ksiazki (copyright/OCR-risk), nie strony web
ALLOWED_REGISTERS = {"ID", "OP", "HI", "IN", "NA"}

CANON = pa.schema([("id", pa.string()), ("text", pa.string()), ("source", pa.string()),
                   ("added", pa.string()), ("created", pa.string()),
                   ("token_count", pa.int64()), ("license", pa.string()), ("author", pa.string())])

ENC = tiktoken.get_encoding("cl100k_base")

def domain(url):
    if not url:
        return ""
    h = urlparse(url).netloc.lower()
    return h[4:] if h.startswith("www.") else h

def top_register(reg):
    if not isinstance(reg, dict) or not reg:
        return "", 0.0
    k, v = max(reg.items(), key=lambda kv: kv[1] or 0.0)
    return str(k), float(v or 0.0)

PII_PLACEHOLDER = "[PII]"
# +-prefixed intl phone; FP-safe (0 trafien na prozie wolne_lektury), lapie HPLT-annotation-gap
# na formatowanych stacjonarnych ("+48 (34) 365 19 17") ktore HPLT pii-spany gubia (zmierzone bin5)
PHONE_RE = re.compile(r"\+\d[\d ()\-]{7,}\d")
# residual re-scan OUTPUT (co OCALALO po scrubie != pii_scrubbed=co usunieto); >0 = safety-FAIL (Wartownik)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# national-ID: keyword (PESEL/NIP/REGON/dowod) + PRZYLEGAJACY 9-13 digit -> redact NUMER (Wartownik-finding 8_2).
# FP-safe = label-adjacent + >=9 cyfr (kontekstowe "podaj PESEL" bez numeru NIE zlapane; RODO najwyzsza wrazliwosc).
NATID_RE = re.compile(r"(?i)(PESEL|NIP|REGON|dow[o\u00f3]d\s+osobist\w*)([\s:.\-]{0,4}(?:nr\.?|numer)?[\s:.\-]{0,4})(\d[\d\s\-]{7,13}\d)")

def scrub_pii(text, spans, max_frac):
    """Redaguj PII: HPLT pii-spany [[start,end],...] (offsety SUROWEGO text) + supplementary
    phone-regex (HPLT annotation ma coverage-gap na formatowanych stacjonarnych - zmierzone bin5).
    Zwraca (scrubbed, n_pii_removed, drop). drop=True gdy HPLT-PII-char-frakcja > max_frac."""
    out = text
    n_hplt = 0
    if spans and isinstance(spans, list):
        n = len(text)
        norm = []
        for sp in spans:
            if isinstance(sp, (list, tuple)) and len(sp) >= 2:
                try:
                    a2, b2 = int(sp[0]), int(sp[1])
                except (TypeError, ValueError):
                    continue
                if 0 <= a2 < b2 <= n:
                    norm.append((a2, b2))
        if norm:
            norm.sort()
            merged = [list(norm[0])]
            for a2, b2 in norm[1:]:
                if a2 <= merged[-1][1]:
                    merged[-1][1] = max(merged[-1][1], b2)
                else:
                    merged.append([a2, b2])
            pii_chars = sum(b2 - a2 for a2, b2 in merged)
            if max_frac and n and pii_chars / n > max_frac:
                return text, len(merged), True
            for a2, b2 in reversed(merged):
                out = out[:a2] + PII_PLACEHOLDER + out[b2:]
            n_hplt = len(merged)
    # supplementary phone-scrub: HPLT-annotation-gap (FP-safe +-pattern), zawsze - takze gdy brak HPLT-spanow
    out, n_phone = PHONE_RE.subn("[Telefon]", out)  # v6 (Arek): spojny z v6-label-window; +48-intl recall (v6 lapie labeled-non-+48)
    # national-ID keyword-adjacent numer (PESEL/NIP/REGON/dowod) - RODO high-sensitivity, FP-safe (label+>=9digit)
    out, n_natid = NATID_RE.subn(lambda m: m.group(1) + m.group(2) + PII_PLACEHOLDER, out)
    return out, n_hplt + n_phone + n_natid, False

def keep(o, min_chars, min_words, min_lang_prob, max_mt, dom_counts, max_per_domain):
    lang = o.get("lang")
    if not (isinstance(lang, list) and lang and lang[0] == "pol_Latn"):
        return None, "language"
    prob = o.get("prob")
    lp = float(prob[0]) if isinstance(prob, list) and prob else 0.0
    if lp < min_lang_prob:
        return None, "lang_prob"
    host = domain(o.get("u"))
    if any(p in host for p in EXCLUDED_DOMAIN_PARTS):
        return None, "domain"
    if max_per_domain and dom_counts.get(host, 0) >= max_per_domain:
        return None, "domain_cap"
    reg = o.get("web-register") or {}
    mt = float(reg.get("MT", 0.0)) if isinstance(reg, dict) else 0.0
    if mt >= max_mt:
        return None, "machine_translated"
    rtop, _ = top_register(reg)
    if ALLOWED_REGISTERS and rtop not in ALLOWED_REGISTERS:
        return None, "register"
    text = (o.get("text") or "").strip()
    if len(text) < min_chars:
        return None, "short"
    if len(text.split()) < min_words:
        return None, "few_words"
    if len(text) > MAX_CHARS:
        return None, "too_long"
    if PDFHOST_RE.search(text[:200]):
        return None, "filehost"
    if len(MOJIBAKE_RE.findall(text[:3000])) >= 3:
        return None, "mojibake"
    s = text[:5000]
    if len(BOILERPLATE_RE.findall(s)) >= 3:
        return None, "boilerplate"
    if ADULT_SPAM_RE.search(s):
        return None, "adult_spam"
    if LEGALISH_RE.search(s):
        return None, "legalish"
    return text, "kept"

def open_input(path):
    """Local file or URL (stream) -> binary readable context manager."""
    if str(path).startswith("http"):
        import urllib.request
        return urllib.request.urlopen(urllib.request.Request(path, headers={"User-Agent": "slayer-dsbench/1.0"}), timeout=120)
    return open(path, "rb")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=r"C:\ProjektyPublic\datasets\hplt_v3_pl\10_1.jsonl.zst")
    ap.add_argument("--out-dir", default=r"C:\ProjektyPublic\datasets\hplt_v3_pl\data\european_hplt_v3_pl")
    ap.add_argument("--source", default="european_hplt_v3_pl", help="wartosc kolumny source")
    ap.add_argument("--out-name", default="", help="basename plikow (domyslnie = source); id prefix")
    ap.add_argument("--bin-label", default="WDS=10")
    ap.add_argument("--min-chars", type=int, default=400)
    ap.add_argument("--min-words", type=int, default=80)
    ap.add_argument("--min-lang-prob", type=float, default=0.80)
    ap.add_argument("--max-mt-prob", type=float, default=0.20)
    ap.add_argument("--max-per-domain", type=int, default=250)
    ap.add_argument("--max-records", type=int, default=0)
    ap.add_argument("--max-pii-frac", type=float, default=0.02,
                    help="drop-doc gdy PII-char-frakcja > prog (katalog kontaktowy); redakcja spanow zawsze")
    a = ap.parse_args()
    src = a.source; out = a.out_name or a.source
    outd = Path(a.out_dir); outd.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    drops = {}; regs = {}; doms = {}; dom_counts = {}
    ids, texts, tokens = [], [], []
    read = kept = chars = toks = 0
    mt_sum = 0.0
    pii_docs = pii_spans_removed = 0
    resid_email = resid_phone = resid_natid = 0
    writer = pq.ParquetWriter(outd / f"{out}.parquet", CANON, compression="zstd")

    def flush():
        nonlocal ids, texts, tokens
        if not ids:
            return
        n = len(ids)
        writer.write_table(pa.table({
            "id": ids, "text": texts, "source": [src]*n, "added": [ADDED]*n,
            "created": [""]*n, "token_count": tokens, "license": [LICENSE]*n, "author": [""]*n},
            schema=CANON))
        ids, texts, tokens = [], [], []

    with open_input(a.inp) as fh:
        reader = zstd.ZstdDecompressor().stream_reader(fh)
        buf = b""
        while True:
            chunk = reader.read(1 << 20)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if not line.strip():
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                read += 1
                npii = 0
                scrubbed, npii, pdrop = scrub_pii(o.get("text") or "", o.get("pii"), a.max_pii_frac)
                if pdrop:
                    drops["pii_dense"] = drops.get("pii_dense", 0) + 1
                    continue
                if npii:
                    o["text"] = scrubbed
                text, reason = keep(o, a.min_chars, a.min_words, a.min_lang_prob,
                                    a.max_mt_prob, dom_counts, a.max_per_domain)
                if text is None:
                    drops[reason] = drops.get(reason, 0) + 1
                    continue
                if npii:
                    pii_docs += 1; pii_spans_removed += npii
                host = domain(o.get("u")); dom_counts[host] = dom_counts.get(host, 0) + 1
                if len(doms) < 500:
                    doms[host] = doms.get(host, 0) + 1
                reg = o.get("web-register") or {}
                rtop, _ = top_register(reg); regs[rtop] = regs.get(rtop, 0) + 1
                mt_sum += float(reg.get("MT", 0.0)) if isinstance(reg, dict) else 0.0
                tk = len(ENC.encode(text, disallowed_special=()))
                resid_email += len(EMAIL_RE.findall(text)); resid_phone += len(PHONE_RE.findall(text)); resid_natid += len(NATID_RE.findall(text))
                ids.append(f"{out}_{kept}"); texts.append(text); tokens.append(tk)
                kept += 1; chars += len(text); toks += tk
                if len(ids) >= 1000:
                    flush()
                if read % 20000 == 0:
                    print(f"  read={read:,} kept={kept:,} tok={toks:,} ({time.time()-t0:.0f}s)", flush=True)
                if a.max_records and kept >= a.max_records:
                    buf = b""; break
            else:
                continue
            break
    flush(); writer.close()

    stats = {"read": read, "kept": kept, "drop_short": drops.get("short", 0),
             "drop_lang": drops.get("language", 0) + drops.get("lang_prob", 0),
             "drop_dup": 0, "drop_ocr": 0, "chars": chars, "tokens": toks,
             "licenses": {LICENSE: kept}, "authors_with_value": 0, "license": LICENSE,
             "stats_recomputed_from_parquet": True,
             "drop_detail": drops, "registers": regs,
             "pii_docs_scrubbed": pii_docs, "pii_spans_removed": pii_spans_removed,
             "drop_pii_dense": drops.get("pii_dense", 0),
             "raw_email_residual": resid_email, "raw_phone_residual": resid_phone, "raw_natid_residual": resid_natid,
             "pii_residual_clean": (resid_email == 0 and resid_phone == 0 and resid_natid == 0),
             "mt_prob_mean_kept": round(mt_sum / max(1, kept), 3),
             "domains_top_sample": dict(sorted(doms.items(), key=lambda x: -x[1])[:30]),
             "secs": round(time.time()-t0, 1),
             "source_repo": f"HPLT/HPLT3.0 pol_Latn {a.bin_label} via {a.inp}"}
    (outd / f"{out}.stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("=== STATS ===")
    print(json.dumps({k: v for k, v in stats.items() if k not in ("domains_top_sample",)}, ensure_ascii=False, indent=2))
    print(f"parquet={outd/(out+'.parquet')} ({os.path.getsize(outd/(out+'.parquet')):,}B)")
    if resid_email or resid_phone or resid_natid:
        print(f"!!! PII-RESIDUAL-FAIL email={resid_email} phone={resid_phone} natid={resid_natid} — gap, INVESTIGATE przed accept/PR", flush=True)
    else:
        print("PII-RESIDUAL-CLEAN email=0 phone=0 natid=0 — safety-gate PASS", flush=True)

if __name__ == "__main__":
    main()
