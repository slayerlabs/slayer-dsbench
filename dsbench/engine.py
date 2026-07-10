"""Orkiestrator: ładuje formatkę (schema + lista checków po ID) i odpala. ZERO nazw pól w kodzie."""
from __future__ import annotations
import json
import pathlib
from .models import Issue, Ctx, Report
from .schema import load_yaml, load_card, validate_declarative
from . import registry
from . import checks as _checks  # noqa: F401  (import rejestruje checki)


def load_records(path) -> list:
    if str(path).lower().endswith(".parquet"):
        return _load_parquet(path)
    recs = []
    with open(path, encoding="utf-8") as f:
        for n, ln in enumerate(f):
            ln = ln.strip()
            if not ln:
                continue
            try:
                recs.append(json.loads(ln))
            except Exception as e:
                recs.append({"__parse_error__": f"linia {n+1}: {e}"})
    return recs


def _load_parquet(path) -> list:
    """Parquet (dynaword/HF) -> lista rekordów. Wymaga pyarrow (opcjonalna zależność).
    Czyta cały plik do pamięci (jak JSONL) — na pełnych blobach podawaj sample/shard."""
    try:
        import pyarrow.parquet as pq
    except Exception as e:
        return [{"__parse_error__": f"parquet wymaga pyarrow (pip install pyarrow): {e}"}]
    try:
        return pq.read_table(path).to_pylist()
    except Exception as e:
        return [{"__parse_error__": f"parquet nieczytelny ({path}): {e}"}]


def audit(card_path, format_path, data_path=None, schema_only=False) -> Report:
    card_path = pathlib.Path(card_path)
    card = load_card(card_path)
    fmt = load_yaml(format_path)
    issues: list = []

    # 1. deklaratywnie: karta wg formatki
    issues += validate_declarative(card, fmt.get("card_schema", {}), "card")

    # 2. rekordy: pełne dane jeśli podane, inaczej próbka z karty (offline-friendly, S2)
    rec_path = data_path
    if not rec_path and card.get("sample"):
        rec_path = card_path.parent / card["sample"]
    records: list = []
    if rec_path and pathlib.Path(rec_path).exists():
        records = load_records(rec_path)
    else:
        issues.append(Issue("error", "load", "data", f"brak danych (data/sample): {rec_path}"))

    # 3. deklaratywnie: rekordy wg record_schema (GENERYCZNIE — formatka steruje, nie kod)
    rs = fmt.get("record_schema", {})
    for i, rec in enumerate(records):
        if "__parse_error__" in rec:
            issues.append(Issue("error", "load", f"record#{i}", rec["__parse_error__"]))
            continue
        issues += validate_declarative(rec, rs, f"record#{i}")

    # 4. checki proceduralne wg LISTY w formatce (po ID z rejestru)
    if not schema_only:
        ctx = Ctx(card=card, formatka=fmt, records=records,
                  data_path=str(rec_path) if rec_path else None, root=card_path.parent)
        for cid in fmt.get("checks", []):
            try:
                issues += registry.get(cid)(ctx)
            except Exception as e:
                issues.append(Issue("error", cid, "check", f"wyjątek: {e}"))

    verdict = "FAIL" if any(i.level == "error" for i in issues) else "PASS"
    return Report(dataset=str(card.get("name", "?")), verdict=verdict, issues=issues)
