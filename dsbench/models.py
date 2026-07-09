"""Modele danych: Issue, Ctx, Report. Zero logiki domenowej."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any

LEVELS = ("error", "warn", "info")


@dataclass
class Issue:
    level: str          # error | warn | info
    check: str          # id checku / "schema" / "load"
    where: str          # gdzie (card / record#N / data)
    msg: str


@dataclass
class Ctx:
    """Kontekst przekazywany do checków. Checki NIE znają nazw pól — biorą je z formatki."""
    card: dict
    formatka: dict
    records: list
    data_path: str | None
    root: Any           # pathlib.Path katalogu karty


@dataclass
class Report:
    dataset: str
    verdict: str        # PASS | FAIL
    issues: list = field(default_factory=list)

    def by_level(self, lvl: str) -> list:
        return [i for i in self.issues if i.level == lvl]

    def to_dict(self) -> dict:
        return {
            "dataset": self.dataset,
            "verdict": self.verdict,
            "errors": len(self.by_level("error")),
            "warnings": len(self.by_level("warn")),
            "issues": [i.__dict__ for i in self.issues],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def to_markdown(self) -> str:
        icon = {"PASS": "✅", "FAIL": "❌"}.get(self.verdict, "?")
        tag = {"error": "❌ BŁĄD", "warn": "⚠️ OSTRZ", "info": "ℹ️ INFO"}
        lines = [f"## dsbench: {self.dataset} — {icon} {self.verdict}",
                 f"_błędy: {len(self.by_level('error'))} · ostrzeżenia: {len(self.by_level('warn'))}_", ""]
        for lvl in LEVELS:
            for i in self.by_level(lvl):
                lines.append(f"- {tag[lvl]} `[{i.check}]` {i.where}: {i.msg}")
        return "\n".join(lines)
