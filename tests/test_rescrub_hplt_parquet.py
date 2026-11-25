from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import tempfile

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from rescrub_hplt_parquet import MANIFEST_NAME, rescrub  # noqa: E402


def test_rescrub_creates_distinct_manifest_bound_artifact():
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        source = root / "v19"
        source.mkdir()
        source_file = source / "shard.parquet"
        original = pa.table(
            {
                "id": ["a", "b", "c"],
                "text": [
                    "tel. 812-787-2734",
                    "nr telefonu: 56 45 10 310",
                    "współrzędne 52.229676, 21.012228",
                ],
            }
        )
        pq.write_table(original, source_file, compression="zstd")
        (source / MANIFEST_NAME).write_text("source-manifest\n", encoding="utf-8", newline="\n")

        output = root / "v20"
        result = rescrub(source, output, batch_size=1)

        assert output.is_dir()
        assert pq.read_table(source_file).equals(original)
        assert pq.read_table(output / "shard.parquet").column("text").to_pylist() == [
            "tel. [Telefon]",
            "nr telefonu: [Telefon]",
            "współrzędne 52.229676, 21.012228",
        ]
        assert result["files"] == 1
        assert result["source_manifest"] == MANIFEST_NAME
        assert result["source_manifest_sha256"] == hashlib.sha256(b"source-manifest\n").hexdigest()
        assert result["documents"] == 3
        assert result["phone_or_mangle_replacements"] == 2
        assert len((output / MANIFEST_NAME).read_text(encoding="utf-8").splitlines()) == 1
        stats = json.loads((output / "rescrub-stats.json").read_text(encoding="utf-8"))
        assert stats == result


def test_rescrub_keeps_large_string_text_column():
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        source = root / "v19"
        source.mkdir()
        text = pa.array(["tel. 812-787-2734"], type=pa.large_string())
        pq.write_table(pa.table({"id": ["a"], "text": text}), source / "shard.parquet")

        rescrub(source, root / "v20")

        column = pq.read_table(root / "v20" / "shard.parquet").column("text")
        assert column.type == pa.large_string()
        assert column.to_pylist() == ["tel. [Telefon]"]


def test_rescrub_failure_leaves_no_output_or_staging():
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        source = root / "v19"
        source.mkdir()
        pq.write_table(pa.table({"id": ["a"], "body": ["tel. 812-787-2734"]}), source / "shard.parquet")

        output = root / "v20"
        try:
            rescrub(source, output)
        except ValueError as error:
            assert "missing text column" in str(error)
            assert sorted(p.name for p in root.iterdir()) == ["v19"]
            # Jeszcze w obsłudze błędu plik wejściowy nie może być trzymany otwarty
            # (na Windows otwarty uchwyt blokuje rename i sprzątanie katalogu).
            (source / "shard.parquet").rename(source / "moved.parquet")
        else:
            pytest.fail("rescrub bez kolumny text nie zgłosił błędu")
