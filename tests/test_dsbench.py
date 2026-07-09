"""Testy dsbench — kryteria S1/S2/S3 + higiena + kompatybilność chat/nested (messages[])."""
from __future__ import annotations
import hashlib
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dsbench.engine import audit  # noqa: E402

V1 = ROOT / "formats" / "v1.yaml"
V2 = ROOT / "formats" / "v2.yaml"
STYLE = ROOT / "formats" / "style-sft.yaml"


def _w(d, name, content):
    p = pathlib.Path(d) / name
    p.write_text(content, encoding="utf-8")
    return p


def _card(d, sample="sample.jsonl", extra=""):
    return _w(d, "card.yaml",
              "name: t\nversion: 0.1.0\nlicense: CC0-1.0\nvisibility: external\n"
              f"source_url: http://x\nsample: {sample}\n{extra}")


def test_sejm_passes():
    assert audit(ROOT / "datasets" / "sejm" / "card.yaml", V1).verdict == "PASS"


def test_style_sft_example_passes():
    rep = audit(ROOT / "datasets" / "style-sft-example" / "card.yaml", STYLE)
    assert rep.verdict == "PASS", rep.to_markdown()


def test_missing_required_field_fails():
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sample.jsonl", '{"speaker":"X"}\n')
        rep = audit(_card(d), V1)
        assert rep.verdict == "FAIL"
        assert any("text" in i.msg for i in rep.by_level("error"))


def test_s1_modularnosc_podmiana_formatki():
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sample.jsonl", '{"id":"a","text":"abc","speaker":"X"}\n')
        card = _card(d)
        assert audit(card, V1).verdict == "PASS"
        r2 = audit(card, V2)
        assert r2.verdict == "FAIL"
        assert any("speaker_count" in i.msg for i in r2.by_level("error"))


def test_s2_integrity_wykrywa_podmiane():
    with tempfile.TemporaryDirectory() as d:
        data = _w(d, "data.jsonl", '{"id":"a","text":"abc"}\n')
        sh = hashlib.sha256(data.read_bytes()).hexdigest()
        card = _card(d, "data.jsonl", extra=f"sha256: {sh}\n")
        assert audit(card, V1, data_path=str(data)).verdict == "PASS"
        data.write_text('{"id":"a","text":"abcd"}\n', encoding="utf-8")
        bad = audit(card, V1, data_path=str(data))
        assert bad.verdict == "FAIL"
        assert any(i.check == "integrity" for i in bad.by_level("error"))


def test_s3_determinizm():
    c = ROOT / "datasets" / "sejm" / "card.yaml"
    assert audit(c, V1).to_dict() == audit(c, V1).to_dict()


def test_pii_pesel_failuje():
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sample.jsonl", '{"id":"a","text":"numer 44051401359 w zdaniu"}\n')
        rep = audit(_card(d), V1)
        assert any(i.check == "pii" and i.level == "error" for i in rep.issues)


def test_pii_NESTED_messages_failuje():
    """Kluczowe: PII w messages[].content MUSI być wykryte (inaczej false-green na formacie chat)."""
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sample.jsonl",
           '{"id":"a","source":"s","messages":[{"role":"user","content":"mój PESEL to 44051401359"}]}\n')
        rep = audit(_card(d), STYLE)
        assert any(i.check == "pii" and i.level == "error" for i in rep.issues), rep.to_markdown()


def test_failloud_gdy_brak_tekstu():
    """Rekord chat + formatka flat (text) → NIC nie wyłuskane → BŁĄD (blokuje merge), nie 'czyste'."""
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sample.jsonl", '{"id":"a","messages":[{"role":"user","content":"hej"}]}\n')
        (pathlib.Path(d) / "eval_sets").mkdir()
        _w(d, "eval_sets/hashes.txt", "deadbeef\n")   # żeby decontam realnie wszedł
        rep = audit(_card(d), V1)  # v1 oczekuje flat 'text'
        assert rep.verdict == "FAIL", rep.to_markdown()
        assert any(i.check == "pii" and i.level == "error" and "wyłuskało" in i.msg for i in rep.issues), rep.to_markdown()
        assert any(i.check == "decontam" and i.level == "error" and "wyłuskało" in i.msg for i in rep.issues), rep.to_markdown()
        assert not any("czyste" in i.msg for i in rep.issues)


def test_dedup_failuje():
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sample.jsonl", '{"id":"a","text":"ten sam"}\n{"id":"b","text":"ten sam"}\n')
        rep = audit(_card(d), V1)
        assert any(i.check == "dedup" and i.level == "error" for i in rep.issues)


def test_uniqueid_dup_failuje():
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sample.jsonl", '{"id":"a","text":"x"}\n{"id":"a","text":"y"}\n')
        rep = audit(_card(d), V1)
        assert any(i.check == "uniqueid" and i.level == "error" for i in rep.issues)


def test_empty_text_failuje():
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sample.jsonl", '{"id":"a","text":"   "}\n')
        rep = audit(_card(d), V1)
        assert any(i.check == "empty" and i.level == "error" for i in rep.issues)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    ok = 0
    for fn in tests:
        try:
            fn()
            print("PASS", fn.__name__)
            ok += 1
        except AssertionError as e:
            print("FAIL", fn.__name__, "-", str(e)[:200])
        except Exception as e:
            print("ERROR", fn.__name__, "-", type(e).__name__, str(e)[:200])
    print(f"\n{ok}/{len(tests)} testów PASS")
    sys.exit(0 if ok == len(tests) else 1)
