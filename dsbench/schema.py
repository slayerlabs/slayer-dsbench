"""Walidacja DEKLARATYWNA (schema-driven). Silnik nie zna nazw pól — czyta je z formatki."""
from __future__ import annotations
import yaml
import pathlib
from .models import Issue

_TYPES = {"str": str, "int": int, "float": (int, float), "number": (int, float),
          "bool": bool, "list": list, "dict": dict}


def load_yaml(path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _frontmatter(text: str):
    """Wyłuskuje blok YAML frontmatter (--- ... ---) z początku pliku .md; None gdy brak."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i])
    return None


def load_card(path) -> dict:
    """Karta: .yaml/.yml → cały plik; .md → YAML-frontmatter (styl HF / slayerlabs/datasets)."""
    path = pathlib.Path(path)
    if path.suffix.lower() == ".md":
        fm = _frontmatter(path.read_text(encoding="utf-8"))
        if fm is None:
            raise ValueError(f"karta .md bez frontmattera YAML (--- na górze pliku): {path}")
        return yaml.safe_load(fm) or {}
    return load_yaml(path)


def validate_declarative(obj, schema: dict, where: str) -> list:
    """Sprawdza obj wg schema['fields'] = {nazwa: {type, required, enum}}. Generyczne — bez hardkodu pól."""
    issues = []
    fields = (schema or {}).get("fields", {})
    if not isinstance(obj, dict):
        return [Issue("error", "schema", where, "nie jest obiektem JSON")]
    for name, spec in fields.items():
        spec = spec or {}
        present = name in obj and obj[name] not in (None, "")
        if not present:
            if spec.get("required"):
                issues.append(Issue("error", "schema", where, f"brak wymaganego pola '{name}'"))
            continue
        val = obj[name]
        t = spec.get("type")
        if t and t in _TYPES and not isinstance(val, _TYPES[t]):
            issues.append(Issue("error", "schema", where,
                                f"pole '{name}': oczekiwano {t}, jest {type(val).__name__}"))
        if "enum" in spec and val not in spec["enum"]:
            issues.append(Issue("error", "schema", where,
                                f"pole '{name}'='{val}' spoza enum {spec['enum']}"))
    return issues
