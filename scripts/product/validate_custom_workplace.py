#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = PROJECT_ROOT / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from custom_workplace import GEOCODING_SOURCE, build_custom_dashboard_data, geocode_address, top1_summary  # noqa: E402
from data_loader import MODE_ORDER  # noqa: E402


OUTPUT_MD = PROJECT_ROOT / "outputs" / "product" / "custom_workplace_validation.md"
TEST_ADDRESSES = [
    "台北市內湖區瑞光路",
    "新北市深坑區北深路三段",
]


def main() -> int:
    lines = [
        "# Custom Workplace Validation",
        "",
        "Scenario: public transit, weekday 08:00 Asia/Taipei, candidate node to user-input workplace coordinates.",
        "",
        f"Geocoding source: {GEOCODING_SOURCE}",
        "",
        "| test address | geocoding | lat | lon | 省租型 Top 1 | 平衡型 Top 1 | 通勤型 Top 1 | 生活品質型 Top 1 | route failures |",
        "|---|---|---:|---:|---|---|---|---|---|",
    ]
    for address in TEST_ADDRESSES:
        route_failures = ""
        try:
            geocode = geocode_address(address)
            _, recommendations, _, _ = build_custom_dashboard_data(address, geocode)
            top1 = top1_summary(recommendations)
            lines.append(
                f"| {address} | success | {float(geocode['lat']):.6f} | {float(geocode['lon']):.6f} | "
                f"{top1['省租型']} | {top1['平衡型']} | {top1['通勤型']} | {top1['生活品質型']} | none |"
            )
            print(
                f"{address}: "
                + ", ".join(f"{mode}={top1[mode]}" for mode in MODE_ORDER)
            )
        except Exception as exc:
            route_failures = str(exc).replace("|", "/")
            lines.append(f"| {address} | failed |  |  |  |  |  |  | {route_failures} |")
            print(f"{address}: failed: {exc}", file=sys.stderr)

    lines += [
        "",
        "Notes:",
        "",
        "- Geocoding results and TDX MaaS responses are cached locally.",
        "- The custom workplace is labeled as `我的工作地`, not as a station.",
        "- This is still candidate-node to workplace-coordinate public transit, not door-to-door commuting.",
    ]
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_MD.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
