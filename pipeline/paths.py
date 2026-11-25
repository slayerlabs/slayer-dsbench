"""Ścieżki wspólne dla skryptów pipeline/ (8x3b, klasyfikator rejestrów).

Pliki repo (eval_sets/, datasets/) liczone względem repo. Dane spoza repo (zbudowany zbiór, warstwy
build/, polish-dynaword) pod katalogiem z DSBENCH_DATA; brak zmiennej = STOP, bez zgadywania ścieżki.
Arkusze do ręcznego przeglądu (.md) idą do DSBENCH_NOTES (domyślnie katalog bieżący).
"""

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EVAL_SETS = REPO / "eval_sets"
DATASETS = REPO / "datasets"


def data_root() -> Path:
    v = os.environ.get("DSBENCH_DATA")
    if not v:
        raise SystemExit(
            "STOP: ustaw DSBENCH_DATA na katalog danych (zawiera slayer-pl-8x3b/, build/, polish-dynaword/)"
        )
    return Path(v)


def notes_dir() -> Path:
    return Path(os.environ.get("DSBENCH_NOTES", "."))
