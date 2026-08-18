# -*- coding: utf-8 -*-
"""Wartownik post-batch DEEP-VERIFY (independent PII-safety gate, 2-arbiter).
Lens NIEZALEZNY od pipeline-scruba: (1) idempotency-residual (re-run scrub_fix = 0?),
(2) broad-independent phone-leak-scan (inny regex, DATE/IBAN/token-excluded, samples->human-judgment),
(3) mangle-scan + auto-clean, (4) over-scrub-sample. FCD-R4: check==scrub-logic dla idempotency;
independent-lens dla misses. date-excluded (lekcja: date-contamination Monter/Latarnik).
Uzycie: python deep_verify.py <parquet>...   (albo glob-dir)
"""
import sys, re, glob
import pyarrow.parquet as pq
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # local pipeline dir
import phone_scrub as M

def scrub_fix(x, cap=8):
    tot = 0
    for _ in range(cap):
        x, n = M.scrub_phones_labelwindow(x); tot += n
        if n == 0: break
    return x, tot

# INDEPENDENT lens (NIE pipeline-PHONE_NUM): broad phone-context + structured 9-11-run, date/IBAN/token-excl
CTX = re.compile(r"(?i)\b(tel|telefon\w*|kom[oó]rk\w*|\bkom\b|kontakt\w*|zadzwo\w*|infolini\w*|gsm|fax\w*|faks\w*|dzwo\w*|zadzw\w*|nr\s*tel)\b")
# real-phone-format: 9-11 digits with structure (spaces/dashes/parens), allow +48 / leading-0
PHONE = re.compile(r"(?<!\d)(?:\+?48[\s\-]?)?(?:0[\s\-]?)?(?:\(?\d{2,3}\)?[\s\-]?){2,4}\d{2,3}(?!\d)")
_DATE = re.compile(r"(?:19|20)\d{2}[\s\-./]\d{1,2}[\s\-./]\d{1,2}|\b\d{1,2}[\s\-./](?:19|20)\d{2}\b")
_TOKEN = re.compile(r"\[(?:Telefon|PII|Email|PESEL|NIP)\]")
MANGLE = re.compile(r"\[Telefon\][-\d]|\d\[Telefon\]")

def independent_leak_scan(text):
    """Broad-lens: real-phone-format w phone-context, EXCLUDE date/IBAN-context/6+zeros. Zwraca [samples]."""
    leaks = []
    for cm in CTX.finditer(text):
        win = text[cm.end():cm.end() + 60]
        for pm in PHONE.finditer(win):
            seg = pm.group()
            d = re.sub(r"\D", "", seg)
            if len(d) < 9 or len(d) > 11: continue
            if re.search(r"0{6,}", d): continue            # sentinel/fake
            if _DATE.search(seg): continue                  # date-exclude (contamination-lekcja)
            if M._KRS.search(seg) or M._ISBN.search(seg): continue
            # NRB/konto: cluster >=16 cyfr (26-cyfrowe NRB) — poza scope (D6), BEZ wymogu kw
            # (lekcja 'internetowego.57 1020 1127...': kw 'konto' nie zawsze przed klastrem)
            gs = cm.end() + pm.start()
            cs = gs
            while cs > 0 and text[cs-1] in "0123456789 -": cs -= 1
            ce = cm.end() + pm.end()
            while ce < len(text) and text[ce] in "0123456789 -": ce += 1
            cluster_digits = sum(c.isdigit() for c in text[cs:ce])
            if cluster_digits >= 20: continue                 # NRB/IBAN (26-28 cyfr, D6: zostaje); 17-19 = dwa numery (kandydat)
            if cluster_digits > 11 and M._ACCT.search(text[max(0,cs-30):cs]): continue  # IBAN-context
            # emergency (112/997/998/999) — publiczne, nie PII
            if re.sub(r"\D", "", seg) in ("112", "997", "998", "999"): continue
            # FP-exclude (v18, z triage b2 na pełnych): KRS-9/BDO-rejestr/IMEI/filename/wersja-jądra/fb-m.me URL
            seg_c = seg.strip()
            ctx45 = text[max(0,gs-45):ce+25]
            if re.match(r"^\d{9}$", seg_c) and re.search(r"(?i)(KRS|BDO|IMEI|rejestr\w*|wersja|\.jpe?g|\.png|facebook|m\.me|www\.|http)", ctx45): continue
            # v19: bare-seg = fragment dłuższej BARE-liczby (count/ID, np. 61541567415841) — FP;
            # liczby ze strukturą (spacje/kreski) zostają (realne, np. 'tel/fax 750 52 82 0660399142')
            if not re.search(r"[\s\-/()]", seg_c) and not re.search(r"[\s\-/()]", text[cs:ce]) and cluster_digits > len(d):
                continue
            leaks.append((cm.group(), seg.strip(), text[max(0,gs-15):ce+5]))
    return leaks

def verify_shard(path):
    t = pq.read_table(path)
    texts = t.column("text").to_pylist() if "text" in t.column_names else []
    n_docs = len(texts)
    idem_resid = 0; leak_docs = 0; leak_samples = []; mangle_docs = 0; mangle_samples = []; tok = 0
    for x in texts:
        if not x: continue
        tok += x.count("[Telefon]")
        _, r = scrub_fix(x)          # idempotency-residual (should be 0)
        idem_resid += r
        lk = independent_leak_scan(x)
        if lk:
            leak_docs += 1
            if len(leak_samples) < 8: leak_samples.extend(lk[:2])
        mg = MANGLE.findall(x)
        if mg:
            mangle_docs += 1
            if len(mangle_samples) < 8:
                m = MANGLE.search(x); mangle_samples.append(x[max(0,m.start()-20):m.end()+15])
    return dict(path=path.split("/")[-1], docs=n_docs, tokens_telefon=tok,
                idem_residual=idem_resid, leak_docs=leak_docs, leak_samples=leak_samples[:8],
                mangle_docs=mangle_docs, mangle_samples=mangle_samples[:8])

def main(paths):
    files = []
    for p in paths:
        files.extend(glob.glob(p)) if ("*" in p or not p.endswith(".parquet")) else files.append(p)
    files = sorted(set(f for f in files if f.endswith(".parquet")))
    agg = dict(docs=0, idem=0, leakd=0, mangled=0, tok=0)
    for f in files:
        r = verify_shard(f)
        agg["docs"] += r["docs"]; agg["idem"] += r["idem_residual"]
        agg["leakd"] += r["leak_docs"]; agg["mangled"] += r["mangle_docs"]; agg["tok"] += r["tokens_telefon"]
        print(f"\n=== {r['path']} ===")
        print(f"  docs={r['docs']} [Telefon]-tok={r['tokens_telefon']} idem-residual={r['idem_residual']} (MUSI 0)")
        print(f"  INDEP-leak-docs={r['leak_docs']}  mangle-docs={r['mangle_docs']}")
        for s in r["leak_samples"]: print(f"    LEAK? {s}")
        for s in r["mangle_samples"]: print(f"    MANGLE: {s!r}")
    d = agg["docs"] or 1
    print(f"\n===== AGGREGATE {len(files)} shards =====")
    print(f"  docs={agg['docs']} [Telefon]-total={agg['tok']}")
    print(f"  idem-residual={agg['idem']} (MUSI 0 = scrub-converged)")
    print(f"  INDEP-leak-docs={agg['leakd']} ({100*agg['leakd']/d:.4f}%)")
    print(f"  mangle-docs={agg['mangled']} ({100*agg['mangled']/d:.4f}%)")
    print(f"  VERDICT: {'GREEN' if agg['idem']==0 and agg['leakd']==0 else 'INVESTIGATE (sprawdz samples)'}")

if __name__ == "__main__":
    main(sys.argv[1:] or [r"C:/Projekty/Slayer/datasets/polish-dynaword-expansion/*.parquet"])
