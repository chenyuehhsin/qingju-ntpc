from __future__ import annotations

from pathlib import Path
import re

import pandas as pd

from src.data_cleaner import STANDARD_DISTRICTS, normalize_district
from src.data_loader import PROJECT_ROOT, RAW_DIR, read_json_rows
from src.sources.base import (
    SourceValidationResult,
    copy_immutable,
    metadata_for_file,
    utcnow_text,
    validate_required_fields,
)


POPULATION_REQUIRED_FIELDS = [
    "statistic_yyymm",
    "site_id",
    *[f"people_age_{age:03d}_{sex}" for age in range(18, 36) for sex in ["m", "f"]],
]


class PopulationSourceAdapter:
    name = "population"
    source_name = "內政部戶政司 ODRP014 村里戶數、單一年齡人口"

    def __init__(self, raw_dir: Path = RAW_DIR, project_root: Path = PROJECT_ROOT) -> None:
        self.raw_dir = raw_dir
        self.project_root = project_root

    def source_paths(self) -> list[Path]:
        return sorted(self.raw_dir.glob("ris_village_single_age_ntpc_*.json"))

    def fetch(self, target_dir: Path, *, dry_run: bool = False, force: bool = False) -> list[Path]:
        sources = self.source_paths()
        if dry_run:
            return [target_dir / source.name for source in sources]
        return [copy_immutable(source, target_dir / source.name, force=force) for source in sources]

    def validate_raw(self, paths: list[Path]) -> SourceValidationResult:
        real_paths = [path for path in paths if path.exists()]
        if not real_paths:
            return SourceValidationResult(False, ["population source unavailable or not yet published"], [], 0)
        errors: list[str] = []
        warnings: list[str] = []
        total_rows = 0
        for path in real_paths:
            df, _metadata = read_json_rows(path)
            total_rows += len(df)
            result = validate_required_fields(list(df.columns), POPULATION_REQUIRED_FIELDS, path.name)
            errors.extend(result.errors)
            warnings.extend([f"{path.name} extra field: {field}" for field in result.warnings])
            districts = df["site_id"].map(normalize_district).dropna().unique().tolist() if "site_id" in df else []
            missing = sorted(set(STANDARD_DISTRICTS) - set(districts))
            if missing:
                errors.append(f"{path.name} missing districts after normalization: {missing}")
        return SourceValidationResult(not errors, errors, warnings, total_rows)

    def extract_reference_date(self, paths: list[Path]) -> str | None:
        months: list[str] = []
        for path in paths:
            if path.exists():
                df, _metadata = read_json_rows(path)
                if "statistic_yyymm" in df:
                    months.extend(df["statistic_yyymm"].dropna().astype(str).unique().tolist())
            match = re.search(r"_(\d{3})(\d{2})_", path.name)
            if match:
                months.append(f"{int(match.group(1)) + 1911:04d}-{int(match.group(2)):02d}")
        normalized = []
        for value in months:
            match = re.fullmatch(r"(\d{3})(\d{2})", value)
            if match:
                normalized.append(f"{int(match.group(1)) + 1911:04d}-{int(match.group(2)):02d}")
                continue
            match = re.fullmatch(r"(\d{4})-(\d{2})", value)
            if match:
                normalized.append(value)
        return sorted(normalized)[-1] if normalized else None

    def normalize(self, paths: list[Path]) -> pd.DataFrame:
        frames = []
        for path in [item for item in paths if item.exists()]:
            df, _metadata = read_json_rows(path)
            working = df.copy()
            working["district"] = working["site_id"].map(normalize_district)
            working = working.dropna(subset=["district"])
            youth_columns = [f"people_age_{age:03d}_{sex}" for age in range(18, 36) for sex in ["m", "f"]]
            working["youth_population_18_35"] = working[youth_columns].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=1)
            frames.append(
                working.groupby("district", as_index=False)["youth_population_18_35"].sum()
            )
        if not frames:
            return pd.DataFrame(columns=["district", "youth_population_18_35"])
        return pd.concat(frames).groupby("district", as_index=False)["youth_population_18_35"].sum()

    def get_provenance(self, paths: list[Path]) -> dict:
        reference_date = self.extract_reference_date(paths)
        files = []
        for path in [item for item in paths if item.exists()]:
            df, _metadata = read_json_rows(path)
            files.append(
                metadata_for_file(
                    path,
                    source=self.source_name,
                    downloaded_at=None,
                    reference_date=reference_date,
                    row_count=len(df),
                    root=self.project_root,
                ).__dict__
            )
        return {
            "reference_month": reference_date,
            "downloaded_at": None,
            "files": files,
            "validated_at": utcnow_text(),
        }
