from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
from pathlib import Path
import shutil
from typing import Protocol

import pandas as pd


@dataclass(frozen=True)
class SourceFileMetadata:
    filename: str
    source: str
    downloaded_at: str | None
    reference_date: str | None
    sha256: str
    row_count: int | None
    size_bytes: int
    path: str


@dataclass(frozen=True)
class SourceValidationResult:
    ok: bool
    errors: list[str]
    warnings: list[str]
    row_count: int | None = None


class SourceAdapter(Protocol):
    name: str

    def fetch(self, target_dir: Path, *, dry_run: bool = False, force: bool = False) -> list[Path]:
        ...

    def validate_raw(self, paths: list[Path]) -> SourceValidationResult:
        ...

    def extract_reference_date(self, paths: list[Path]) -> str | None:
        ...

    def normalize(self, paths: list[Path]) -> pd.DataFrame:
        ...

    def get_provenance(self, paths: list[Path]) -> dict:
        ...


def utcnow_text() -> str:
    return datetime.now().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_immutable(source: Path, target: Path, *, force: bool = False) -> Path:
    if target.exists() and not force:
        raise FileExistsError(f"Raw snapshot file already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def metadata_for_file(
    path: Path,
    *,
    source: str,
    downloaded_at: str | None,
    reference_date: str | None,
    row_count: int | None,
    root: Path,
) -> SourceFileMetadata:
    return SourceFileMetadata(
        filename=path.name,
        source=source,
        downloaded_at=downloaded_at,
        reference_date=reference_date,
        sha256=sha256_file(path),
        row_count=row_count,
        size_bytes=path.stat().st_size,
        path=str(path.relative_to(root)),
    )


def validate_required_fields(columns: list[str], required: list[str], source_name: str) -> SourceValidationResult:
    missing = [field for field in required if field not in columns]
    warnings = [field for field in columns if field not in required]
    if missing:
        return SourceValidationResult(False, [f"{source_name} missing required fields: {missing}"], warnings)
    return SourceValidationResult(True, [], warnings)
