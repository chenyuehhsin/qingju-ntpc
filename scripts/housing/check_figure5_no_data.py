from __future__ import annotations

import geopandas as gpd
import pandas as pd

from common import INTERIM_HOUSING, OUTPUT_HOUSING, PROCESSED_HOUSING, ensure_output_dirs


BENCHMARK_CSV = PROCESSED_HOUSING / "moi_independent_suite_rent_benchmark.csv"
BOUNDARY_EXTRACT_DIR = INTERIM_HOUSING / "boundaries" / "nlsc_town_boundary_twd97"
OUTPUT_MD = OUTPUT_HOUSING / "figure5_no_data_check.md"


def main() -> None:
    ensure_output_dirs()
    shapefiles = list(BOUNDARY_EXTRACT_DIR.rglob("*.shp"))
    if not shapefiles:
        raise FileNotFoundError(f"No boundary shapefile found under {BOUNDARY_EXTRACT_DIR}")
    boundary_path = max(shapefiles, key=lambda path: path.stat().st_size)

    boundaries = gpd.read_file(boundary_path, encoding="utf-8")
    ntpc_boundaries = boundaries[boundaries["COUNTYNAME"] == "新北市"].copy()
    boundary_districts = sorted(ntpc_boundaries["TOWNNAME"].tolist())

    benchmark = pd.read_csv(BENCHMARK_CSV)
    ntpc_benchmark = benchmark[benchmark["city"] == "新北市"].copy()
    benchmark_districts = sorted(ntpc_benchmark["district"].tolist())

    boundary_set = set(boundary_districts)
    benchmark_set = set(benchmark_districts)
    no_data_districts = sorted(boundary_set - benchmark_set)
    benchmark_not_in_boundary = sorted(benchmark_set - boundary_set)

    joined = ntpc_boundaries.merge(
        ntpc_benchmark[["district", "rent_median"]],
        left_on="TOWNNAME",
        right_on="district",
        how="left",
        indicator=True,
    )
    join_failures = sorted(
        joined.loc[(joined["_merge"] == "left_only") & joined["TOWNNAME"].isin(benchmark_set), "TOWNNAME"].tolist()
    )
    joined_no_data = sorted(joined.loc[joined["rent_median"].isna(), "TOWNNAME"].tolist())
    no_data_due_to_source_missing = joined_no_data == no_data_districts and not benchmark_not_in_boundary and not join_failures

    lines = [
        "# Figure 5 No Data Check",
        "",
        f"Boundary shapefile: `{boundary_path.as_posix()}`",
        f"Benchmark CSV: `{BENCHMARK_CSV.as_posix()}`",
        "",
        "## 1. New Taipei Boundary Districts",
        "",
        f"Count: {len(boundary_districts)}",
        "",
        ", ".join(boundary_districts),
        "",
        "## 2. New Taipei Districts With MOI Benchmark Data",
        "",
        f"Count: {len(benchmark_districts)}",
        "",
        ", ".join(benchmark_districts),
        "",
        "## 3. No Data Districts",
        "",
        f"Count: {len(no_data_districts)}",
        "",
        ", ".join(no_data_districts) if no_data_districts else "None",
        "",
        "## 4. Join Validation",
        "",
        f"Benchmark districts not found in boundary: {', '.join(benchmark_not_in_boundary) if benchmark_not_in_boundary else 'None'}",
        f"Join failures for benchmark districts: {', '.join(join_failures) if join_failures else 'None'}",
        f"Districts rendered as No Data after join: {', '.join(joined_no_data) if joined_no_data else 'None'}",
        "",
        f"Conclusion: {'Gray No Data areas come entirely from benchmark missing values, not district-name join failures.' if no_data_due_to_source_missing else 'No Data areas may include join failures; inspect the lists above before using Figure 5.'}",
    ]
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUTPUT_MD}")
    print(f"boundary_count={len(boundary_districts)} benchmark_count={len(benchmark_districts)} no_data_count={len(no_data_districts)}")
    print("no_data=" + (", ".join(no_data_districts) if no_data_districts else "None"))
    print("join_failures=" + (", ".join(join_failures) if join_failures else "None"))


if __name__ == "__main__":
    main()
