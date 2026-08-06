"""Testy checku `artifacts` (skan artefaktów kodowania/ekstrakcji). Izolacja przez custom-formatkę
(`checks: [artifacts]`) — check jest default we wszystkich formatkach, tu testowany osobno.
Broni kontraktu detektorów (empiria polish-dynaword, smoke-verified 2026-08-06):
  ENCODING (error, zero-FP): U+FFFD, Latin-2 mojibake ¶±³¼¿ mid-word.
  FP-safety: math/standalone ± (5±5, ±5%) i obce æêñ (Næringsliv) NIE liczone jako mojibake.
  STRUKTURALNE (warn, FP-prone): mid-word '?' — ostrzeżenie, NIE error (osądź próbką)."""
from __future__ import annotations
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dsbench.engine import audit  # noqa: E402


def _w(d, name, content):
    p = pathlib.Path(d) / name
    p.write_text(content, encoding="utf-8")
    return p


def _card(d, sample="sample.jsonl"):
    return _w(d, "card.yaml",
              "name: t\nversion: 0.1.0\nlicense: CC0-1.0\nvisibility: external\n"
              f"source_url: http://x\nsample: {sample}\n")


def _fmt(d):
    return _w(d, "fmt.yaml",
              "name: t\nversion: 1\ntext_fields: [text]\nid_field: id\n"
              "record_schema:\n  fields:\n    text: {type: str, required: true}\n"
              "checks: [artifacts]\n")


def _arts(rep):
    return [i for i in rep.issues if i.check == "artifacts"]


def test_ufffd_jest_bledem():
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sample.jsonl", '{"id":"a","text":"uszkodzony \ufffd bajt w tekscie"}\n')
        rep = audit(_card(d), _fmt(d))
        assert any(i.level == "error" and "FFFD" in i.msg for i in _arts(rep)), rep.to_markdown()


def test_latin2_mojibake_jest_bledem():
    """¶=ś ±=ą ³=ł między literami → error (recoverable-remap)."""
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sample.jsonl", '{"id":"a","text":"Statek na Wi\u00b6le plynal rozs\u00b1dnym tempem g\u00b3adko."}\n')
        rep = audit(_card(d), _fmt(d))
        assert any(i.level == "error" and "mojibake" in i.msg.lower() for i in _arts(rep)), rep.to_markdown()


def test_math_i_obce_litery_nie_sa_mojibake():
    """FP-safe: math/standalone ± (5±5, ±5%) i obce æ (Næringsliv) → BRAK błędu mojibake."""
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sample.jsonl",
           '{"id":"a","text":"Pomiar 5\u00b15 stopni w zakresie \u00b15% normy pomiarowej."}\n'
           '{"id":"b","text":"Norweska gazeta Dagens N\u00e6ringsliv opisala sprawe."}\n')
        rep = audit(_card(d), _fmt(d))
        assert not any(i.level == "error" and "mojibake" in i.msg.lower() for i in _arts(rep)), rep.to_markdown()


def test_midword_pytajnik_to_warn_nie_error():
    """mid-word '?' = FP-prone (charset-artefakt + brak-spacji/URL) → warn, NIGDY error."""
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sample.jsonl", '{"id":"a","text":"zdanie rozs?dne ale watch?v= to URL nie defekt"}\n')
        rep = audit(_card(d), _fmt(d))
        arts = _arts(rep)
        assert any(i.level == "warn" and "?" in i.msg for i in arts), rep.to_markdown()
        assert not any(i.level == "error" and "?" in i.msg for i in arts), rep.to_markdown()


def test_czysta_proza_bez_artefaktow():
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sample.jsonl", '{"id":"a","text":"Nad Wisla rosly wierzby a dzieci graly w pilke wieczorem."}\n')
        rep = audit(_card(d), _fmt(d))
        assert not any(i.level == "error" for i in _arts(rep)), rep.to_markdown()
