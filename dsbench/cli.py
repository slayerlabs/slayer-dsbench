"""CLI — cienki adapter nad silnikiem (ten sam kod co CI). Karta może deklarować `format`."""
from __future__ import annotations
import argparse
import pathlib
import sys
from .engine import audit
from .schema import load_card
from . import registry

CARD_TEMPLATE = """name: <nazwa>
version: 0.1.0
license: <SPDX, np. CC0-1.0>
collection_license: CC0-1.0
visibility: external          # external | internal
format: v1                    # która formatka (formats/<format>.yaml)
source_url: <URL do danych (HF / release)>
sha256: <opcjonalnie: sha256 pełnego pliku danych>
sample: sample.jsonl
records: 0
"""
SAMPLE_TEMPLATE = '{"id": "x-0001", "text": "przykladowy rekord", "date": "2026-01-01"}\n'


def _resolve_format(card_path, fmt_arg):
    if fmt_arg:
        return fmt_arg
    try:
        name = str(load_card(card_path).get("format") or "v1")
    except Exception:
        name = "v1"
    return f"formats/{name}.yaml"


def _run(a, schema_only):
    fmt = _resolve_format(a.card, a.format)
    rep = audit(a.card, fmt, a.data, schema_only=schema_only)
    print(rep.to_json() if a.json else rep.to_markdown())
    return 0 if rep.verdict == "PASS" else 1


def cmd_audit(a):
    return _run(a, False)


def cmd_validate(a):
    return _run(a, True)


def cmd_card(a):
    return _run(a, False)


def cmd_init(a):
    p = pathlib.Path(a.path)
    p.mkdir(parents=True, exist_ok=True)
    card = p / "card.yaml"
    if card.exists() and not a.force:
        print(f"istnieje: {card} (użyj --force)")
        return 1
    card.write_text(CARD_TEMPLATE, encoding="utf-8")
    (p / "sample.jsonl").write_text(SAMPLE_TEMPLATE, encoding="utf-8")
    print(f"utworzono: {card} + sample.jsonl")
    return 0


def cmd_checks(a):
    print("dostępne checki:", ", ".join(registry.names()))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="dsbench", description="Bramka walidacji datasetów (schema-agnostyczna)")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--card", required=True, help="ścieżka do card.yaml")
        sp.add_argument("--format", default=None, help="formatka (domyślnie z pola `format` karty → formats/<f>.yaml)")
        sp.add_argument("--data", default=None, help="pełny plik danych (domyślnie: próbka z karty)")
        sp.add_argument("--json", action="store_true", help="raport JSON zamiast markdown")

    sp = sub.add_parser("audit", help="pełny audyt (schema + checki)"); common(sp); sp.set_defaults(fn=cmd_audit)
    sp = sub.add_parser("validate", help="tylko schema"); common(sp); sp.set_defaults(fn=cmd_validate)
    sp = sub.add_parser("card", help="raport-karta (markdown)"); common(sp); sp.set_defaults(fn=cmd_card)
    sp = sub.add_parser("init", help="szkielet karty"); sp.add_argument("path"); sp.add_argument("--force", action="store_true"); sp.set_defaults(fn=cmd_init)
    sp = sub.add_parser("checks", help="lista checków"); sp.set_defaults(fn=cmd_checks)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
