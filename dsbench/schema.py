"""Walidacja DEKLARATYWNA (schema-driven). Silnik nie zna nazw pól — czyta je z formatki."""
from __future__ import annotations
import yaml
from .models import Issue

_TYPES = {"str": str, "int": int, "float": (int, float), "number": (int, float),
          "bool": bool, "list": list, "dict": dict}


def load_yaml(path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


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
