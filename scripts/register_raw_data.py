#!/usr/bin/env python3
"""Register a manually downloaded raw dataset.

This tool copies or moves a local file into data/raw/<category>/ using the
project naming convention, then appends a provenance record to data/data_catalog.csv.
It does not inspect or modify file contents.
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
from pathlib import Path


CATALOG_COLUMNS = [
    "dataset_id",
    "filename",
    "original_filename",
    "category",
    "source_org",
    "source_url",
    "download_date",
    "data_period",
    "geographic_scope",
    "format",
    "description",
    "raw_or_derived",
    "notes",
]

SNAKE_CASE_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PERIOD_RE = re.compile(r"^\d{4}-\d{2}(?:-\d{2})?$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy or move a manually downloaded raw dataset into data/raw and update the catalog."
    )
    parser.add_argument("--file", required=True, help="Path to the downloaded source file.")
    parser.add_argument("--category", required=True, help="Raw data category, for example housing.")
    parser.add_argument("--source-org", required=True, help="Source organization key, for example ntpc or moi.")
    parser.add_argument("--name", required=True, help="Dataset name in snake_case, for example rental_transactions.")
    parser.add_argument("--download-date", required=True, help="Download date in YYYY-MM-DD format.")
    parser.add_argument("--source-url", default="", help="Source URL, if known.")
    parser.add_argument("--data-period", default="", help="Data period in YYYY-MM or YYYY-MM-DD format.")
    parser.add_argument("--geographic-scope", default="", help="Geographic coverage, for example New Taipei City.")
    parser.add_argument("--description", default="", help="Short dataset description.")
    parser.add_argument("--notes", default="", help="Additional catalog notes.")
    parser.add_argument("--move", action="store_true", help="Move the source file instead of copying it.")
    return parser.parse_args()


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def validate_args(args: argparse.Namespace) -> Path:
    source_path = Path(args.file).expanduser().resolve()
    if not source_path.exists():
        fail(f"source file does not exist: {source_path}")
    if not source_path.is_file():
        fail(f"source path is not a file: {source_path}")

    for field_name in ("category", "source_org", "name"):
        value = getattr(args, field_name.replace("-", "_"))
        if not SNAKE_CASE_RE.match(value):
            fail(f"--{field_name.replace('_', '-')} must be lowercase snake_case: {value!r}")

    if not DATE_RE.match(args.download_date):
        fail("--download-date must use YYYY-MM-DD format")

    if args.data_period and not PERIOD_RE.match(args.data_period):
        fail("--data-period must use YYYY-MM or YYYY-MM-DD format")

    if not source_path.suffix:
        fail("source file must have an extension")

    return source_path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def unique_destination(raw_dir: Path, stem: str, suffix: str) -> Path:
    candidate = raw_dir / f"{stem}{suffix}"
    if not candidate.exists():
        return candidate

    version = 2
    while True:
        candidate = raw_dir / f"{stem}_v{version}{suffix}"
        if not candidate.exists():
            print(
                f"Destination exists; using versioned filename instead: {candidate}",
                file=sys.stderr,
            )
            return candidate
        version += 1


def ensure_catalog(catalog_path: Path) -> None:
    if catalog_path.exists():
        with catalog_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != CATALOG_COLUMNS:
                fail(
                    "catalog columns do not match expected schema. "
                    f"Expected {CATALOG_COLUMNS}, got {reader.fieldnames}"
                )
        return

    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    with catalog_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CATALOG_COLUMNS)
        writer.writeheader()


def append_catalog_record(catalog_path: Path, record: dict[str, str]) -> None:
    with catalog_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CATALOG_COLUMNS)
        writer.writerow(record)


def main() -> int:
    args = parse_args()
    source_path = validate_args(args)

    root = project_root()
    raw_dir = root / "data" / "raw" / args.category
    raw_dir.mkdir(parents=True, exist_ok=True)

    suffix = source_path.suffix.lower()
    stem = f"{args.source_org}_{args.name}_{args.download_date}"
    destination = unique_destination(raw_dir, stem, suffix)

    if args.move:
        shutil.move(str(source_path), str(destination))
        action = "moved"
    else:
        shutil.copy2(source_path, destination)
        action = "copied"

    catalog_path = root / "data" / "data_catalog.csv"
    ensure_catalog(catalog_path)

    relative_destination = destination.relative_to(root).as_posix()
    dataset_id = destination.stem
    record = {
        "dataset_id": dataset_id,
        "filename": relative_destination,
        "original_filename": source_path.name,
        "category": args.category,
        "source_org": args.source_org,
        "source_url": args.source_url,
        "download_date": args.download_date,
        "data_period": args.data_period,
        "geographic_scope": args.geographic_scope,
        "format": suffix.lstrip("."),
        "description": args.description,
        "raw_or_derived": "raw",
        "notes": args.notes,
    }
    append_catalog_record(catalog_path, record)

    print(f"Raw file {action}: {relative_destination}")
    print("Catalog record:")
    writer = csv.DictWriter(sys.stdout, fieldnames=CATALOG_COLUMNS)
    writer.writeheader()
    writer.writerow(record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
