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
MCQ = ROOT / "formats" / "mcq.yaml"


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


def test_mcq_example_passes():
    rep = audit(ROOT / "datasets" / "mcq-example" / "card.yaml", MCQ)
    assert rep.verdict == "PASS", rep.to_markdown()


def test_pii_nested_options_failuje():
    """PII w options[] (lista STRINGÓW) MUSI być wykryte (mcq nested-aware)."""
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sample.jsonl",
           '{"id":"a","question":"pytanie?","options":["ok","mój PESEL to 44051401359"],"answer":0}\n')
        rep = audit(_card(d), MCQ)
        assert any(i.check == "pii" and i.level == "error" for i in rep.issues), rep.to_markdown()


def test_md_frontmatter_card_passes():
    """Karta .md z YAML-frontmatterem ładuje się i przechodzi audyt (styl slayerlabs/datasets)."""
    rep = audit(ROOT / "datasets" / "style-md-example" / "card.md", STYLE)
    assert rep.verdict == "PASS", rep.to_markdown()


def test_cli_resolwuje_format_z_md():
    """CLI dobiera formatkę z pola `format` karty .md (nie domyślne v1)."""
    from dsbench.cli import _resolve_format
    md = ROOT / "datasets" / "style-md-example" / "card.md"
    assert _resolve_format(md, None) == "formats/style-sft.yaml"
    assert _resolve_format(md, "formats/v1.yaml") == "formats/v1.yaml"  # explicit ma pierwszeństwo


def test_cli_audit_smoke():
    """Pełna ścieżka CLI (import audit + _run) — łapie zerwane importy, których testy engine nie widzą."""
    from dsbench.cli import main
    rc = main(["audit", "--card", str(ROOT / "datasets" / "mcq-example" / "card.yaml"), "--format", str(MCQ)])
    assert rc == 0


def test_license_per_record_restricted_failuje():
    """external + rekord z licencją NC (CC-BY-NC-4.0) → błąd license/data → FAIL."""
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sample.jsonl",
           '{"id":"a","text":"Pierwszy dokument otwarty.","source":"sejm","license":"CC0-1.0"}\n'
           '{"id":"b","text":"Drugi dokument niekomercyjny.","source":"lektury","license":"CC-BY-NC-4.0"}\n'
           '{"id":"c","text":"Trzeci dokument otwarty.","source":"lektury","license":"CC-BY-SA-3.0"}\n')
        rep = audit(_card(d), V1)
        assert rep.verdict == "FAIL", rep.to_markdown()
        assert any(i.check == "license" and i.level == "error" and i.where == "data"
                   for i in rep.issues), rep.to_markdown()


def test_license_per_record_unknown_ostrzega():
    """external + jedna licencja nierozpoznana (Proprietary), reszta otwarta →
    warn license/data, ale BEZ błędu (nierozpoznana sama w sobie nie failuje)."""
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sample.jsonl",
           '{"id":"a","text":"Dokument otwarty pierwszy.","source":"src-a","license":"CC0-1.0"}\n'
           '{"id":"b","text":"Dokument o licencji wlasnosciowej.","source":"src-b","license":"Proprietary"}\n'
           '{"id":"c","text":"Dokument otwarty drugi.","source":"src-a","license":"CC0-1.0"}\n')
        rep = audit(_card(d), V1)
        assert any(i.check == "license" and i.level == "warn" and i.where == "data"
                   for i in rep.issues), rep.to_markdown()
        assert not any(i.check == "license" and i.level == "error"
                       for i in rep.issues), rep.to_markdown()


def test_license_per_record_open_passes():
    """external + rekordy wyłącznie otwarte (CC0/CC-BY-SA) + jeden bez pola licencji →
    brak błędu license, info per-źródło w data, PASS."""
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sample.jsonl",
           '{"id":"a","text":"Pierwszy otwarty dokument.","source":"biblioteka","license":"CC0-1.0"}\n'
           '{"id":"b","text":"Drugi otwarty dokument.","source":"archiwum","license":"CC-BY-SA-3.0"}\n'
           '{"id":"c","text":"Trzeci dokument bez licencji per-rekord."}\n')
        rep = audit(_card(d), V1)
        assert not any(i.check == "license" and i.level == "error"
                       for i in rep.issues), rep.to_markdown()
        assert any(i.check == "license" and i.level == "info" and i.where == "data"
                   and "per źródło" in i.msg for i in rep.issues), rep.to_markdown()
        assert rep.verdict == "PASS", rep.to_markdown()


def test_license_per_record_dormant_gdy_brak_pola():
    """Rekordy bez pola licencji (styl sejm) pod V1 → ścieżka per-rekord uśpiona:
    brak jakiegokolwiek issue license w data; parasol karty (info license/card) nadal jest."""
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sample.jsonl",
           '{"id":"a","text":"Zwykly rekord bez licencji.","speaker":"Posel X"}\n'
           '{"id":"b","text":"Inny rekord bez pola licencji.","speaker":"Posel Y"}\n')
        rep = audit(_card(d), V1)
        assert not any(i.check == "license" and i.where == "data"
                       for i in rep.issues), rep.to_markdown()
        assert any(i.check == "license" and i.where == "card"
                   for i in rep.issues), rep.to_markdown()
        assert rep.verdict == "PASS", rep.to_markdown()


def test_is_open_odrzuca_nc_nd():
    """Bugfix: NC/ND NIE są otwarte mimo prefiksu CC-BY; SA/CC0/MIT są otwarte."""
    from dsbench.checks.license import _is_open
    assert _is_open("CC-BY-NC-4.0") is False
    assert _is_open("CC-BY-ND-4.0") is False
    assert _is_open("CC-BY-SA-3.0") is True
    assert _is_open("CC0-1.0") is True
    assert _is_open("MIT") is True


def test_license_manifest_nc_failuje():
    """external + source_manifest: rekordy niosą tylko `source` (bez license); manifest mapuje
    src_b→CC-BY-NC-4.0 → efektywna licencja NC pod external → error license/data → FAIL."""
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sources.yaml", "sources:\n  src_a: {license: CC0-1.0}\n  src_b: {license: CC-BY-NC-4.0}\n")
        _w(d, "sample.jsonl",
           '{"id":"a","text":"Pierwszy dokument z wolnego zrodla.","source":"src_a"}\n'
           '{"id":"b","text":"Drugi dokument z niekomercyjnego zrodla.","source":"src_b"}\n')
        rep = audit(_card(d, extra="source_manifest: sources.yaml\n"), V1)
        assert rep.verdict == "FAIL", rep.to_markdown()
        assert any(i.check == "license" and i.level == "error" and i.where == "data"
                   and ("NIE-otwart" in i.msg or "CC-BY-NC" in i.msg)
                   for i in rep.issues), rep.to_markdown()


def test_license_manifest_unknown_ostrzega():
    """external + manifest z UNKNOWN dla jednego źródła (reszta otwarta) → warn license/data,
    BEZ błędu (nierozpoznana per-źródło nie failuje) → PASS."""
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sources.yaml", "sources:\n  src_a: {license: CC0-1.0}\n  src_c: {license: UNKNOWN}\n")
        _w(d, "sample.jsonl",
           '{"id":"a","text":"Dokument z otwartego zrodla.","source":"src_a"}\n'
           '{"id":"b","text":"Dokument ze zrodla o nieznanej licencji.","source":"src_c"}\n')
        rep = audit(_card(d, extra="source_manifest: sources.yaml\n"), V1)
        assert rep.verdict == "PASS", rep.to_markdown()
        assert any(i.check == "license" and i.level == "warn" and i.where == "data"
                   for i in rep.issues), rep.to_markdown()
        assert not any(i.check == "license" and i.level == "error"
                       for i in rep.issues), rep.to_markdown()


def test_license_manifest_rekord_nadpisuje():
    """Licencja w rekordzie WYGRYWA nad manifestem: manifest src_b→CC-BY-ND-4.0, ale rekord
    niesie license: CC0-1.0 → brak błędu; INFO per-źródło pokazuje CC0-1.0 (nie ND)."""
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sources.yaml", "sources:\n  src_b: {license: CC-BY-ND-4.0}\n")
        _w(d, "sample.jsonl",
           '{"id":"a","text":"Rekord z wlasna licencja otwarta.","source":"src_b","license":"CC0-1.0"}\n')
        rep = audit(_card(d, extra="source_manifest: sources.yaml\n"), V1)
        assert not any(i.check == "license" and i.level == "error"
                       for i in rep.issues), rep.to_markdown()
        info = [i for i in rep.issues
                if i.check == "license" and i.level == "info" and i.where == "data"
                and "per źródło" in i.msg]
        assert info, rep.to_markdown()
        assert "CC0-1.0" in info[0].msg and "ND" not in info[0].msg, info[0].msg


def test_license_manifest_brak_pliku_failuje():
    """Karta wskazuje source_manifest, ale plik nie istnieje → error license/data
    ('source_manifest' + 'brak pliku') → FAIL."""
    with tempfile.TemporaryDirectory() as d:
        _w(d, "sample.jsonl",
           '{"id":"a","text":"Rekord odwolujacy sie do brakujacego manifestu.","source":"src_a"}\n')
        rep = audit(_card(d, extra="source_manifest: sources.yaml\n"), V1)
        assert rep.verdict == "FAIL", rep.to_markdown()
        assert any(i.check == "license" and i.level == "error" and i.where == "data"
                   and "source_manifest" in i.msg and "brak pliku" in i.msg
                   for i in rep.issues), rep.to_markdown()


def test_license_manifest_plaski_i_zagniezdzony():
    """Obie formy manifestu — płaska {src: SPDX} ORAZ zagnieżdżona {sources: {src: {license: SPDX}}}
    — dają ten sam wynik: INFO per-źródło wymienia src_a i src_c, verdykt PASS."""
    data = ('{"id":"a","text":"Dokument z pierwszego zrodla.","source":"src_a"}\n'
            '{"id":"b","text":"Dokument z trzeciego zrodla.","source":"src_c"}\n')
    manifests = {
        "plaski": "src_a: CC0-1.0\nsrc_c: UNKNOWN\n",
        "zagniezdzony": "sources:\n  src_a: {license: CC0-1.0}\n  src_c: {license: UNKNOWN}\n",
    }
    for wariant, manifest in manifests.items():
        with tempfile.TemporaryDirectory() as d:
            _w(d, "sources.yaml", manifest)
            _w(d, "sample.jsonl", data)
            rep = audit(_card(d, extra="source_manifest: sources.yaml\n"), V1)
            assert rep.verdict == "PASS", f"{wariant}: {rep.to_markdown()}"
            assert any(i.check == "license" and i.level == "info" and i.where == "data"
                       and "per źródło" in i.msg and "src_a" in i.msg and "src_c" in i.msg
                       for i in rep.issues), f"{wariant}: {rep.to_markdown()}"


def test_public_domain_liczy_sie_jako_otwarte():
    """dynaword: 'public-domain (official documents)' (parliamentary/dziennik_ustaw) jest OTWARTE, nie WARN."""
    from dsbench.checks.license import _is_open
    assert _is_open("public-domain (official documents)") is True
    assert _is_open("CC-BY-2.5") is True
    assert _is_open("CC-BY-SA-4.0 / Wolna Sztuka 1.3") is True


def test_loader_parquet_czyta_rekordy():
    """Silnik czyta .parquet (dynaword/HF), nie tylko JSONL — po rozszerzeniu pliku."""
    import pyarrow as pa, pyarrow.parquet as pq
    from dsbench.engine import load_records
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "s.parquet"
        pq.write_table(pa.table({"id": ["a", "b"], "text": ["abc", "def"],
                                 "source": ["x", "x"], "license": ["CC-BY-4.0", "CC-BY-4.0"]}), p)
        recs = load_records(str(p))
        assert [r["id"] for r in recs] == ["a", "b"]
        assert recs[0]["text"] == "abc" and recs[0]["license"] == "CC-BY-4.0"


def test_audit_parquet_data_path_passes():
    """Audyt z --data wskazującym .parquet (external, licencja otwarta per-dok) → PASS."""
    import pyarrow as pa, pyarrow.parquet as pq
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "data.parquet"
        pq.write_table(pa.table({"id": ["a"], "text": ["Neutralny tekst encyklopedyczny."],
                                 "source": ["wikipedia"], "license": ["CC-BY-SA-3.0"]}), p)
        rep = audit(_card(d), V1, data_path=str(p))
        assert rep.verdict == "PASS", rep.to_markdown()


def test_dynaword_sample_passes():
    """Realny fixture polish-dynaword (12 źródeł, licencje otwarte) → PASS, zero błędów i ostrzeżeń."""
    rep = audit(ROOT / "datasets" / "polish-dynaword" / "card.yaml", V1)
    assert rep.verdict == "PASS", rep.to_markdown()
    assert not rep.by_level("warn"), rep.to_markdown()


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
