# -*- coding: utf-8 -*-
"""polish_dataset.py — post-process bin-parquet: naprawia bledy z QC-review Arka.
Fix 1: leading 'Strona X z Y' header strip.
Fix 2: intra-word '?' artefakt (upstream HPLT diacritic-loss, lc-PL?lc-PL non-URL) -> usun '?'.
Fix 3: block-level frame_merge: strip CONTIGUOUS runy >=MINRUN high-doc-freq linii (menu/nav-bloki),
       ZOSTAW izolowane high-freq linie (Pozdrawiam/Witam = conversational, nie template). FP-safe.
Niedestrukcyjnie: bez --apply = dry-run + pokazuje co by uciete (FP-check)."""
import re, argparse, glob
from collections import Counter
import pyarrow as pa, pyarrow.parquet as pq

_ws=re.compile(r"\s+")
def norm(l): return _ws.sub(" ", l.strip())
STRONA=re.compile(r"^\s*(Strona\s+\d+\s+z\s+\d+|Str\.?\s*\d+\s*/\s*\d+)\b.*?(\n|$)", re.I)
DASHONLY=re.compile(r"^[\-–—·•\*\s]{1,4}$")  # linia = sam myslnik/punkt/krotki separator (Arka '-\nJakby')
# intra-word '?': lowercase-PL ? lowercase-PL, nie w URL (bez =,http,www,.php,.html w poblizu -> per-match check)
QMID=re.compile(r"([a-ząćęłńóśźż])\?([a-ząćęłńóśźż])")
URLish=re.compile(r"[=]|https?://|www\.|\.php|\.html|\.aspx")

def strip_qmark(text):
    out=[]; n=0
    for line in text.split("\n"):
        if "?" in line and not URLish.search(line):
            line2=QMID.sub(r"\1\2", line)  # usun '?' miedzy malymi literami PL
            n+= line.count("?")-line2.count("?"); line=line2
        out.append(line)
    return "\n".join(out), n

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--parquet", required=True)
    ap.add_argument("--min-ratio", type=float, default=0.004, help="doc-freq prog linii-boilerplate")
    ap.add_argument("--min-run", type=int, default=3, help="min dlugosc CIAGLEGO runu high-freq linii = blok (izolowane zostaja)")
    ap.add_argument("--apply", action="store_true")
    a=ap.parse_args()
    fp=glob.glob(a.parquet)[0]
    t=pq.read_table(fp); cols={c:t.column(c).to_pylist() for c in t.column_names}; tx=cols["text"]; N=len(tx)
    # pass1: line doc-freq
    df=Counter()
    for x in tx:
        df.update({norm(l) for l in x.split("\n") if len(norm(l))>=3})
    thr=max(2,int(a.min_ratio*N)); hi={k for k,c in df.items() if c>=thr}
    # per-doc polish
    strona_hits=qmark_hits=block_lines_removed=leadlist_hits=junk_hits=fffd_hits=0; blocks_removed=0; sample_blocks=[]
    outtx=[]
    for x in tx:
        x2=x
        if "\ufffd" in x2: x2=x2.replace("\ufffd",""); fffd_hits+=1  # U+FFFD replacement-char (decode-junk, Arka '[znak]ci')
        m=STRONA.match(x2)
        if m: x2=x2[m.end():]; strona_hits+=1
        # leading-junk: strip startowe linie ktore sa samym myslnikiem/punktem (Arka '-\nJakby' -> 'Jakby')
        lj=x2.split("\n"); k0=0; had=False
        while k0<len(lj) and (norm(lj[k0])=="" or DASHONLY.match(norm(lj[k0]))):
            if DASHONLY.match(norm(lj[k0])): had=True
            k0+=1
        if k0>0: x2="\n".join(lj[k0:]).lstrip("\n"); junk_hits+= 1 if had else 0
        # leading nav-list block: run >=5 kolejnych '- '/'•' linii na starcie = nav/related-links/teaser (Arka pet-menu)
        ll=x2.split("\n"); s=0
        while s<len(ll) and norm(ll[s])=="": s+=1
        r=s
        while r<len(ll) and (norm(ll[r]).startswith(("- ","• ","· ","– ")) or norm(ll[r])==""): r+=1
        nb=sum(1 for k in range(s,r) if norm(ll[k]))
        if nb>=5:
            x2="\n".join(ll[r:]).strip(); leadlist_hits+=1
        x2,q=strip_qmark(x2); qmark_hits+=q
        # block frame_merge: mark hi-freq lines, strip contiguous runs>=min_run
        lines=x2.split("\n"); mark=[norm(l) in hi and len(norm(l))>=3 for l in lines]
        keep=[True]*len(lines); i=0
        while i<len(lines):
            if mark[i]:
                j=i
                while j<len(lines) and mark[j]: j+=1
                if j-i>=a.min_run:
                    for k in range(i,j): keep[k]=False
                    block_lines_removed+=j-i; blocks_removed+=1
                    if len(sample_blocks)<8: sample_blocks.append(" | ".join(norm(lines[k]) for k in range(i,min(j,i+4))))
                i=j
            else: i+=1
        x2="\n".join(l for l,k in zip(lines,keep) if k).strip()
        outtx.append(x2)
    ch0=sum(len(x) for x in tx); ch1=sum(len(x) for x in outtx)
    short=sum(1 for x in outtx if len(x)<200)
    print(f"{fp.split(chr(92))[-1]}: N={N}")
    print(f"  Strona-header strip: {strona_hits} docs")
    print(f"  intra-word '?' usuniete: {qmark_hits}")
    print(f"  block-frame strip: {blocks_removed} blokow / {block_lines_removed} linii (runy>={a.min_run} hi-freq)")
    print(f"  leading-nav-list strip: {leadlist_hits} docs")
    print(f"  leading-junk (bare-dash) strip: {junk_hits} docs")
    print(f"  U+FFFD (decode-junk) strip: {fffd_hits} docs")
    print(f"  chars {ch0:,}->{ch1:,} ({100*(ch0-ch1)/ch0:.1f}%) | docs<200-po: {short}")
    print("  -- sample stripped-blocks (FP-check czy menu/nav) --")
    for s in sample_blocks: print("    ", repr(s[:90]))
    if a.apply:
        keep=[i for i,x in enumerate(outtx) if len(x)>=200]
        cols["text"]=outtx
        newcols={c:[cols[c][i] for i in keep] for c in cols}
        pq.write_table(pa.table(newcols,schema=t.schema), fp, compression="zstd")
        print(f"  APPLIED -> {fp} ({len(keep)}/{N}, drop {N-len(keep)} short-po-polish)")

if __name__=="__main__": main()
