#!/usr/bin/env python3
"""Create a distinct, atomically-promoted re-scrubbed HPLT Parquet artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from auto_clean_mangle import clean as clean_mangle
from phone_scrub import scrub_phones_labelwindow


MANIFEST_NAME = "SHA256SUMS"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scrub_text(text: str) -> tuple[str, int]:
    total = 0
    for _ in range(8):
        text, changed = scrub_phones_labelwindow(text)
        total += changed
        if changed == 0:
            break
    else:
        raise RuntimeError("phone scrub did not converge in eight passes")
    text, mangles = clean_mangle(text)
    return text, total + mangles


def write_manifest(output_dir: Path, files: list[Path]) -> str:
    manifest = "".join(f"{sha256(path)}  {path.name}\n" for path in files)
    (output_dir / MANIFEST_NAME).write_text(manifest, encoding="utf-8", newline="\n")
    return hashlib.sha256(manifest.encode("utf-8")).hexdigest()


def rescrub(input_dir: Path, output_dir: Path, batch_size: int = 10_000) -> dict:
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"output directory already exists: {output_dir}")
    files = sorted(input_dir.glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"no Parquet files in {input_dir}")

    staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.staging-", dir=output_dir.parent))
    changed = documents = 0
    try:
        outputs = []
        for source in files:
            destination = staging / source.name
            reader = pq.ParquetFile(source)
            writer = pq.ParquetWriter(destination, reader.schema_arrow, compression="zstd")
            try:
                for batch in reader.iter_batches(batch_size=batch_size):
                    table = pa.Table.from_batches([batch])
                    text_index = table.schema.get_field_index("text")
                    if text_index < 0:
                        raise ValueError(f"missing text column: {source}")
                    scrubbed = []
                    for text in table.column(text_index).to_pylist():
                        if not isinstance(text, str):
                            raise ValueError(f"non-string text column value: {source}")
                        value, count = scrub_text(text)
                        scrubbed.append(value)
                        changed += count
                    table = table.set_column(text_index, "text", pa.array(scrubbed, type=pa.string()))
                    writer.write_table(table)
                    documents += table.num_rows
            finally:
                writer.close()
            outputs.append(destination)

        manifest_sha256 = write_manifest(staging, outputs)
        summary = {
            "source_manifest_sha256": sha256(input_dir / MANIFEST_NAME) if (input_dir / MANIFEST_NAME).is_file() else None,
            "files": len(outputs),
            "documents": documents,
            "phone_or_mangle_replacements": changed,
            "manifest_sha256": manifest_sha256,
        }
        (staging / "rescrub-stats.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
        os.replace(staging, output_dir)
        return summary
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--batch-size", type=int, default=10_000)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    print(json.dumps(rescrub(args.input_dir, args.output_dir, args.batch_size), sort_keys=True))


if __name__ == "__main__":
    main()
