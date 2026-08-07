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
_PLLET="a-zA-Z\u0105\u0107\u0119\u0142\u0144\u00f3\u015b\u017a\u017c\u0104\u0106\u0118\u0141\u0143\u00d3\u015a\u0179\u017b"
LATIN2={"\u00b6":"\u015b","\u00b1":"\u0105","\u00b3":"\u0142","\u00bc":"\u017a","\u00bf":"\u017c"}  # Latin-2/CP1250 mojibake: ¶=ś ±=ą ³=ł ¼=ź ¿=ż
MOJI=re.compile(r"(?<=["+_PLLET+r"])([\u00b6\u00b1\u00b3\u00bc\u00bf])(?=["+_PLLET+r"])")  # MID-WORD (litera-obie-strony) = zero-FP (odróżnia 'materia³' od legit 'm³'/'5±2')
# heavily-garbled doc signal (FP-safe): (a) ±-po-małej-literze (=ą-mojibake, legit ± jest digit±digit),
# (b) ¶/¹/¬ letter-adjacent (rzadko legit), (c) ³/¼/¿ adjacent do INNEGO mojibake (_NB) = klaster-garbage
# (np "å¼wirowa"/"ciê¿ko"; Mierniczy sub-klasa). NIE samotne ³/¼/¿/£ (m³/¼/¿hiszp/£funt) ani obce ää (Pääbo) = accept-gap.
_LO="a-z\u0105\u0107\u0119\u0142\u0144\u00f3\u015b\u017a\u017c"
_NB="\u00b6\u00b1\u00b9\u00ac\u00a3\u00e5\u00e4\u00e6\u00ea\u00eb\u00f1\u00a1\u00af\u00a2"  # mojibake-neighbor (klaster-detekcja, NIE ³¼¿ same)
GARBLED=re.compile(r"(?<=["+_LO+r"])\u00b1|(?<=["+_LO+r"])[\u00b6\u00b9\u00ac]|[\u00b6\u00b9\u00ac](?=["+_LO+r"])|(?<=["+_NB+r"])[\u00b3\u00bc\u00bf]|[\u00b3\u00bc\u00bf](?=["+_NB+r"])")
# intra-word '?': lowercase-PL ? lowercase-PL, nie w URL (bez =,http,www,.php,.html w poblizu -> per-match check)
QMID=re.compile(r"([a-ząćęłńóśźż])\?([a-ząćęłńóśźż])")
URLish=re.compile(r"[=]|https?://|www\.|\.php|\.html|\.aspx")
# UTF-8-double-encode mojibake (utf-8 bajty zdekodowane jako cp1252): "zwiÄ…zku"=związku (Mierniczy).
# LOWERCASE-only (FP-safe: 2-char z continuation; bare Å/Ã legit szwedz/portug NIE ruszane).
UTF8DE={"\u00c4\u2026":"\u0105","\u00c4\u2021":"\u0107","\u00c4\u2122":"\u0119","\u00c5\u201a":"\u0142","\u00c5\u201e":"\u0144","\u00c3\u00b3":"\u00f3","\u00c5\u203a":"\u015b","\u00c5\u00ba":"\u017a","\u00c5\u00bc":"\u017c"}
UTF8DE_RE=re.compile("|".join(re.escape(k) for k in UTF8DE))
# leading-boilerplate (Arka 9_3 findingi): button-block · adblock/cookie-notice · asterisk-decorator · template-header · warn.
BTN=re.compile(r"(?i)\b(kliknij|zaloguj|wypr[o\u00f3]buj|zobacz|zarejestruj|dowiedz|tutaj|wejd[z\u017a]|sprawd[z\u017a]|przeczytaj|odwied[z\u017a]|do[l\u0142][a\u0105]cz|czytaj|odkryj)\b")
HDR=re.compile(r"(?i)^(spis tre[s\u015b]ci|ciek\w+ teksty|showing results|archive (for|of)|strony zwi[a\u0105]zane|kategorie?|menu|nawigacja|tagi|tags)\b")
NOTICE=re.compile(r"(?i)(oprogramowania blokuj|adblock|do wyj[a\u0105]tk[o\u00f3]w|blokuj\w* .{0,12}reklam|wy[s\u015b]wietlani\w* reklam|przychod\w* z reklam|serwis\w* utrzymuj\w* si[e\u0119] dzi[e\u0119]ki|dzi[e\u0119]kujemy za zrozumienie|kliknij.{0,15}zamkn|komunikat nie wy[s\u015b]wietli|(u[z\u017c]ywa|wykorzystuje|korzysta|obs[l\u0142]uga|wymagana)\w?\s.{0,25}cookie|akceptuj\w* .{0,15}cookie)")
WARN=re.compile(r"(?i)^[\s!]*(wa[z\u017c]ne|uwaga|ostrze[z\u017c]enie)[\s!:]*$")
def _is_btn(l): n=len(BTN.findall(l)); return n>=3 or (" - " in l and n>=2)  # button-block-line (repeated-link, NIE pojedyncze 'tutaj')
def _is_hdr(l): s=l.strip(); return len(s)<50 and (bool(HDR.match(s)) or (s.endswith(":") and len(s.split())<=4))
def _is_notice(l): return bool(NOTICE.search(l))  # adblock/cookie-consent (strong)
def _is_aster(l): s=l.strip(); return s.startswith("***") or l.count("*")>=8  # asterisk-decorator/separator (strong)
def _is_warn(l): return bool(WARN.match(l.strip()))  # "!!! WAŻNE !!!" (weak, tylko w triggered-region)
def strip_button_block(x):
    """Strip leading boilerplate region (button/notice/asterisk/header/warn) do realnego kontentu.
    FP-safe: region MUSI zawierac >=1 STRONG signal (btn/notice/aster); stop na realnym zdaniu."""
    lines=x.split("\n"); i=0
    while i<len(lines) and (_is_btn(lines[i]) or _is_hdr(lines[i]) or _is_notice(lines[i]) or _is_aster(lines[i]) or _is_warn(lines[i])): i+=1
    if i>0 and any(_is_btn(lines[j]) or _is_notice(lines[j]) or _is_aster(lines[j]) for j in range(i)):
        return "\n".join(lines[i:]).lstrip("\n"), True
    return x, False

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
    strona_hits=qmark_hits=block_lines_removed=leadlist_hits=junk_hits=fffd_hits=latin2_hits=utf8de_hits=btn_hits=0; blocks_removed=0; sample_blocks=[]
    outtx=[]
    for x in tx:
        x2=x
        if "\ufffd" in x2: x2=x2.replace("\ufffd",""); fffd_hits+=1  # U+FFFD replacement-char (decode-junk, Arka '[znak]ci')
        if any(c in x2 for c in LATIN2):
            x2n=MOJI.sub(lambda m: LATIN2[m.group(1)], x2)
            if x2n!=x2: x2=x2n; latin2_hits+=1  # Latin-2 mid-word mojibake remap (¶±³¼¿->śąłźż)
        if "\u00c4" in x2 or "\u00c5" in x2 or "\u00c3\u00b3" in x2:
            x2n=UTF8DE_RE.sub(lambda m: UTF8DE[m.group()], x2)
            if x2n!=x2: x2=x2n; utf8de_hits+=1  # UTF-8-double-encode recovery (cp1252->utf-8, Mierniczy)
        x2n,hit=strip_button_block(x2)
        if hit: x2=x2n; btn_hits+=1  # leading button/link-block strip (Arka finding 9_3)
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
    print(f"  Latin-2 mojibake remap (¶±³¼¿->śąłźż): {latin2_hits} docs")
    print(f"  UTF-8-double-encode recovery (cp1252->utf-8): {utf8de_hits} docs")
    print(f"  button/link-block leading strip (Arka 9_3): {btn_hits} docs")
    garbled=sum(1 for x in outtx if len(x)>=200 and GARBLED.search(x))
    print(f"  chars {ch0:,}->{ch1:,} ({100*(ch0-ch1)/ch0:.1f}%) | docs<200-po: {short} | heavily-garbled drop: {garbled}")
    print("  -- sample stripped-blocks (FP-check czy menu/nav) --")
    for s in sample_blocks: print("    ", repr(s[:90]))
    if a.apply:
        keep=[i for i,x in enumerate(outtx) if len(x)>=200 and not GARBLED.search(x)]
        cols["text"]=outtx
        newcols={c:[cols[c][i] for i in keep] for c in cols}
        pq.write_table(pa.table(newcols,schema=t.schema), fp, compression="zstd")
        print(f"  APPLIED -> {fp} ({len(keep)}/{N}, drop {N-len(keep)}: short-po-polish + heavily-garbled)")

if __name__=="__main__": main()
