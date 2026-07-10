#!/usr/bin/env python3
"""lint-math-unicode — twarda reguła Slayer: matematyka ZAWSZE w LaTeX, nigdy unicode.

Skanuje pliki `.tex` (renderowana treść) i `.md` (dokumenty-metodyka) szukając
matematycznego unicode (greka + relacje/operatory + podwójne strzałki). Łapie np.
U+0394 (Δ), który łamie inputenc w LaTeX, oraz `≥`/`≠`/`⟂` w prozie — żeby dokumenty
NIE łamały reguły, którą same głoszą.

Świadomie NIE łapie: polskich znaków (ąćęłńóśźż), typograficznych separatorów (·),
pojedynczych strzałek w prozie (→ ↔), emoji (⭐ ✅).

Pomijane (nie renderują matematyki): komentarze (`%` w .tex, `<!-- -->` w .md),
bloki kodu ``` ``` ``` ``` oraz inline `code` w .md — tam żyją zamierzone „złe przykłady"
(`$\\perp$` nie `⟂`). Pozycje są zachowane (wymazujemy spacjami, nie skracamy).

Użycie:
  python3 scripts/lint-math-unicode.py szablon-dokumentu          # tylko .tex
  python3 scripts/lint-math-unicode.py docs README.md AGENTS.md   # .md
  python3 scripts/lint-math-unicode.py .                          # całe repo
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

BAD = set(
    "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩαβγδεζηθικλμνξοπρστυφχψω"
    "≤≥≠≈±×÷√∞∑∏∫∂∇⟂∈∉⊂⊆⊇∪∩∀∃⇒⇔≅≡∝∅"
)

FENCE = re.compile(r"```.*?```", re.DOTALL)        # blok kodu markdown
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)  # komentarz HTML/markdown
INLINE_CODE = re.compile(r"`[^`]*`")               # inline code w markdown
TEX_COMMENT = re.compile(r"(?<!\\)%.*$", re.MULTILINE)  # komentarz LaTeX


def blank(match: re.Match) -> str:
    """Zamień dopasowanie na białe znaki tej samej długości (zachowaj numery linii)."""
    return re.sub(r"[^\n]", " ", match.group(0))


def strip_noise(text: str, suffix: str) -> str:
    if suffix == ".md":
        text = HTML_COMMENT.sub(blank, text)
        text = FENCE.sub(blank, text)
        text = INLINE_CODE.sub(blank, text)
    elif suffix == ".tex":
        text = TEX_COMMENT.sub(blank, text)
    return text


def iter_files(paths: list[str]):
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for suf in (".tex", ".md"):
                yield from sorted(p.rglob(f"*{suf}"))
        elif p.suffix in (".tex", ".md"):
            yield p


def main(argv: list[str]) -> int:
    paths = argv or ["."]
    hits = []
    for f in iter_files(paths):
        cleaned = strip_noise(f.read_text(encoding="utf-8"), f.suffix)
        for i, line in enumerate(cleaned.splitlines(), 1):
            for ch in line:
                if ch in BAD:
                    hits.append((f, i, ch))
    if hits:
        print("Unicode matematyczny poza LaTeX/kodem — użyj $...$ (np. $\\ge$, $\\ne$, $\\perp$, $\\Delta$):")
        for f, i, ch in hits[:80]:
            print(f"  {f.as_posix()}:{i}  «{ch}» (U+{ord(ch):04X})")
        if len(hits) > 80:
            print(f"  … i {len(hits) - 80} więcej")
        return 1
    print("OK: brak unicode matematycznego w treści — zgodne z twardą regułą formatki.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
