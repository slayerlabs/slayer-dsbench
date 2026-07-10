#!/usr/bin/env python3
"""generate-ledger — auto-spis węzłów dialektycznych do docs/INDEX.md.

Skanuje docs/**/*.md, czyta frontmatter (type/id/title/status/parents/synthesizes)
i wstawia między znaczniki `<!-- LEDGER:START ... -->` / `<!-- LEDGER:END -->`
KOMPLETNY indeks: Cele · Nitki (Teza ↔ Antyteza → Synteza, rekonstruowane z relacji) ·
Decyzje · Pozostałe węzły. Dzięki temu INDEX ma JEDNO źródło prawdy (frontmatter), bez
ręcznych tabel obok auto-ledgera. Bez zależności zewnętrznych (sam stdlib).

Użycie:
  python3 scripts/generate-ledger.py          # przepisz INDEX.md w miejscu
  python3 scripts/generate-ledger.py --check   # tylko sprawdź (CI); exit 1 gdy nieaktualny
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
INDEX = DOCS / "INDEX.md"

BLOCK_RE = re.compile(
    r"(<!-- LEDGER:START.*?-->)(.*?)(<!-- LEDGER:END -->)",
    re.DOTALL,
)


def parse_frontmatter(text: str) -> dict | None:
    """Minimalny parser frontmatteru YAML — CELOWO ograniczony.

    Obsługuje tylko płaskie `key: value` + inline-listy (`["a","b"]`). NIE obsługuje
    wielowierszowych skalarów blokowych (`|`, `>`) ani map zagnieżdżonych — frontmatter
    węzła jest z założenia płaski (type/id/title/status/parents/...). Brak zależności (pyyaml)
    jest świadomym wyborem: skrypt ma działać na czystym stdlib w CI.
    """
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    if lines[0].strip() != "---":
        return None
    fm: dict[str, str] = {}
    for i in range(1, len(lines)):
        line = lines[i]
        if line.strip() == "---":
            return fm
        m = re.match(r"^([A-Za-z_][\w]*):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return None  # brak zamykającego ---


def clean_scalar(val: str) -> str:
    val = val.strip()
    if len(val) >= 2 and val[0] in "\"'" and val[-1] == val[0]:
        val = val[1:-1]
    return val


def clean_list(val: str) -> list[str]:
    val = val.strip()
    if val.startswith("[") and val.endswith("]"):
        val = val[1:-1]
    return [s for s in (clean_scalar(x) for x in val.split(",")) if s]


def collect_nodes(docs_dir: Path) -> list[dict]:
    """Parametryzowane (docs_dir) dla testowalności."""
    nodes = []
    for path in sorted(docs_dir.rglob("*.md")):
        if path.name in ("_TEMPLATE.md", "INDEX.md"):
            continue
        fm = parse_frontmatter(path.read_text(encoding="utf-8"))
        if not fm or "id" not in fm or "type" not in fm:
            continue
        node_id = clean_scalar(fm["id"])
        if "<" in node_id or ">" in node_id:  # nieuzupełniony placeholder szablonu
            continue
        nodes.append(
            {
                "id": node_id,
                "type": clean_scalar(fm.get("type", "")),
                "title": clean_scalar(fm.get("title", "")),
                "status": clean_scalar(fm.get("status", "")),
                "parents": clean_list(fm.get("parents", "")),
                "synthesizes": clean_list(fm.get("synthesizes", "")),
                "path": path.relative_to(docs_dir).as_posix(),
            }
        )
    nodes.sort(key=lambda n: (n["path"].rsplit("/", 1)[0] if "/" in n["path"] else "", n["id"]))
    return nodes


def _link(node: dict | None) -> str:
    if not node:
        return "—"
    title = node["title"] or node["id"]
    return f"[{node['id']}]({node['path']})"


def render_ledger(nodes: list[dict]) -> str:
    if not nodes:
        return (
            "> **Ledger** (auto): brak węzłów — skopiuj `_TEMPLATE.md` z role-foldera, "
            "nadaj `id`, i uruchom ponownie `python3 scripts/generate-ledger.py`."
        )

    by_type = lambda t: [n for n in nodes if n["type"] == t]
    cele, tezy = by_type("cel"), by_type("teza")
    antytezy, syntezy, decyzje = by_type("antyteza"), by_type("synteza"), by_type("decyzja")
    rdzen = {"cel", "teza", "antyteza", "synteza", "decyzja"}
    inne = [n for n in nodes if n["type"] not in rdzen]

    out = [f"> **Ledger** (auto, {len(nodes)} węzłów). NIE edytuj ręcznie — `scripts/generate-ledger.py`.", ""]

    out.append("### Cele")
    if cele:
        out += ["| id | cel | status | plik |", "|---|---|---|---|"]
        out += [f"| {c['id']} | {c['title'] or '—'} | {c['status']} | {_link(c)} |" for c in cele]
    else:
        out.append("_(brak — dodaj węzeł `type: cel` z `00-Cele/_TEMPLATE.md`)_")
    out.append("")

    out.append("### Nitki dialektyczne (Teza ↔ Antyteza → Synteza)")
    if tezy:
        out += ["| Teza | Antyteza | Synteza | status |", "|---|---|---|---|"]
        for t in tezy:
            at = next((a for a in antytezy if t["id"] in a["parents"]), None)
            s = next((x for x in syntezy if t["id"] in x["synthesizes"] or t["id"] in x["parents"]), None)
            status = (s or t)["status"]
            out.append(f"| {_link(t)} | {_link(at)} | {_link(s)} | {status} |")
    else:
        out.append("_(brak — dodaj `type: teza` + `antyteza` + `synteza`)_")
    out.append("")

    out.append("### Decyzje (ADR)")
    if decyzje:
        out += ["| id | tytuł | status | plik |", "|---|---|---|---|"]
        out += [f"| {d['id']} | {d['title'] or '—'} | {d['status']} | {_link(d)} |" for d in decyzje]
    else:
        out.append("_(brak — ADR w `20-Decyzje/`)_")
    out.append("")

    out.append("### Pozostałe węzły (reference / runbook / ewaluacja / …)")
    if inne:
        out += ["| id | typ | tytuł | status | plik |", "|---|---|---|---|---|"]
        out += [f"| {n['id']} | {n['type']} | {n['title'] or '—'} | {n['status']} | {_link(n)} |" for n in inne]
    else:
        out.append("_(brak)_")

    return "\n".join(out)


def build_index_text() -> str:
    original = INDEX.read_text(encoding="utf-8")
    ledger = render_ledger(collect_nodes(DOCS))

    def repl(m: re.Match) -> str:
        return f"{m.group(1)}\n{ledger}\n{m.group(3)}"

    new_text, count = BLOCK_RE.subn(repl, original)
    if count == 0:
        sys.stderr.write(
            "BŁĄD: nie znaleziono znaczników <!-- LEDGER:START --> / <!-- LEDGER:END --> w docs/INDEX.md\n"
        )
        sys.exit(2)
    return new_text


def main() -> int:
    if not INDEX.exists():
        sys.stderr.write(f"BŁĄD: brak {INDEX}\n")
        return 2
    check = "--check" in sys.argv[1:]
    new_text = build_index_text()
    current = INDEX.read_text(encoding="utf-8")
    if check:
        if new_text != current:
            sys.stderr.write(
                "Ledger w docs/INDEX.md jest NIEAKTUALNY. Uruchom: python3 scripts/generate-ledger.py\n"
            )
            return 1
        print("OK: ledger aktualny.")
        return 0
    if new_text != current:
        INDEX.write_text(new_text, encoding="utf-8", newline="\n")
        print(f"Zaktualizowano {INDEX.relative_to(REPO_ROOT).as_posix()} (ledger).")
    else:
        print("Bez zmian: ledger już aktualny.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
