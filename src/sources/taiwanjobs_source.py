from __future__ import annotations

import json
from pathlib import Path
import re

import pandas as pd

from src.data_cleaner import STANDARD_DISTRICTS, detect_mapping, normalize_district, normalize_work_type, parse_number
from src.data_loader import PROJECT_ROOT, RAW_DIR, read_xml_rows
from src.sources.base import (
    SourceValidationResult,
    copy_immutable,
    metadata_for_file,
    utcnow_text,
)


TAIWANJOBS_REQUIRED_FRAGMENTS = {
    "district": ["CITYNAME"],
    "openings": ["JOB_PERSON"],
    "salary_min": ["NT_L"],
    "salary_max": ["NT_U"],
    "category": ["CJOB_NAME1"],
    "title": ["OCCU_DESC"],
    "company": ["COMPNAME"],
    "updated_at": ["TRANDATE"],
}

DGPA_REQUIRED_FIELDS = ["ORG_NAME", "TITLE", "NUMBER_OF", "WORK_ADDRESS", "DATE_FROM", "DATE_TO"]


class JobSourceAdapter:
    name = "jobs"
    source_name = "台灣就業通與行政院人事行政總處事求人"

    def __init__(self, raw_dir: Path = RAW_DIR, project_root: Path = PROJECT_ROOT) -> None:
        self.raw_dir = raw_dir
        self.project_root = project_root

    def source_paths(self) -> list[Path]:
        taiwanjobs = sorted((self.raw_dir / "taiwanjobs").glob("*.xml"))
        dgpa = [self.raw_dir / "dgpa_public_sector_jobs.xml"] if (self.raw_dir / "dgpa_public_sector_jobs.xml").exists() else []
        return [*taiwanjobs, *dgpa]

    def fetch(self, target_dir: Path, *, dry_run: bool = False, force: bool = False) -> list[Path]:
        sources = self.source_paths()
        targets = []
        for source in sources:
            subdir = "taiwanjobs" if "taiwanjobs" in source.name else "public_sector"
            target = target_dir / subdir / source.name
            targets.append(target)
            if not dry_run:
                copy_immutable(source, target, force=force)
        return targets

    def validate_raw(self, paths: list[Path]) -> SourceValidationResult:
        real_paths = [path for path in paths if path.exists()]
        if not real_paths:
            return SourceValidationResult(False, ["job sources unavailable or not yet published"], [], 0)
        errors: list[str] = []
        warnings: list[str] = []
        total_rows = 0
        districts_seen: set[str] = set()
        for path in real_paths:
            df, _metadata = read_xml_rows(path)
            total_rows += len(df)
            if "taiwanjobs" in path.name:
                columns_text = " ".join(df.columns)
                for logical, fragments in TAIWANJOBS_REQUIRED_FRAGMENTS.items():
                    if not any(fragment in columns_text for fragment in fragments):
                        errors.append(f"{path.name} missing required TaiwanJobs field for {logical}: {fragments}")
                mapping = detect_mapping(df)
                district_source = mapping.address or mapping.district
                if district_source:
                    districts_seen.update(df[district_source].map(normalize_district).dropna().astype(str).unique().tolist())
            else:
                for field in DGPA_REQUIRED_FIELDS:
                    if field not in df.columns:
                        errors.append(f"{path.name} missing required DGPA field: {field}")
                if "WORK_ADDRESS" in df:
                    districts_seen.update(df["WORK_ADDRESS"].map(normalize_district).dropna().astype(str).unique().tolist())
            extra = [column for column in df.columns if column not in DGPA_REQUIRED_FIELDS]
            warnings.extend([f"{path.name} observed field: {column}" for column in extra[:8]])
        missing = sorted(set(STANDARD_DISTRICTS) - districts_seen)
        if missing:
            errors.append(f"job sources missing districts after normalization: {missing}")
        return SourceValidationResult(not errors, errors, warnings, total_rows)

    def extract_reference_date(self, paths: list[Path]) -> str | None:
        dates: list[str] = []
        for path in [item for item in paths if item.exists()]:
            df, _metadata = read_xml_rows(path)
            for column in df.columns:
                if "TRANDATE" in column or column in {"DATE_FROM", "DATE_TO"}:
                    dates.extend(df[column].dropna().astype(str).tolist())
        normalized = []
        for value in dates:
            match = re.fullmatch(r"(\d{4})(\d{2})(\d{2})", value.strip())
            if match:
                normalized.append(f"{match.group(1)}-{match.group(2)}-{match.group(3)}")
        return sorted(normalized)[-1] if normalized else None

    def normalize(self, paths: list[Path]) -> pd.DataFrame:
        rows: list[dict] = []
        for path in [item for item in paths if item.exists()]:
            df, _metadata = read_xml_rows(path)
            mapping = detect_mapping(df)
            district_source = mapping.address or mapping.district
            if not district_source:
                continue
            for _idx, row in df.iterrows():
                district = normalize_district(row.get(district_source))
                if pd.isna(district):
                    continue
                rows.append(
                    {
                        "district": district,
                        "title": row.get(mapping.occupation) if mapping.occupation else None,
                        "company": row.get(mapping.company) if mapping.company else None,
                        "category": row.get(mapping.job_category) if mapping.job_category else None,
                        "openings": parse_number(row.get(mapping.job_openings)) if mapping.job_openings else pd.NA,
                        "work_type": normalize_work_type(row.get(mapping.work_type)) if mapping.work_type else pd.NA,
                        "source_file": path.name,
                    }
                )
        return pd.DataFrame(rows)

    def get_provenance(self, paths: list[Path]) -> dict:
        reference_date = self.extract_reference_date(paths)
        manifest_path = self.raw_dir / "taiwanjobs_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        downloads = [source.get("downloaded_at") for source in manifest.get("sources", []) if source.get("downloaded_at")]
        files = []
        for path in [item for item in paths if item.exists()]:
            df, _metadata = read_xml_rows(path)
            files.append(
                metadata_for_file(
                    path,
                    source=self.source_name,
                    downloaded_at=max(downloads) if downloads else None,
                    reference_date=reference_date,
                    row_count=len(df),
                    root=self.project_root,
                ).__dict__
            )
        return {
            "snapshot_as_of": max(downloads) if downloads else None,
            "downloaded_at": max(downloads) if downloads else None,
            "latest_job_reference_date": reference_date,
            "files": files,
            "validated_at": utcnow_text(),
        }
