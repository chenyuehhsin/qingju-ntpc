from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlretrieve

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
TAIWANJOBS_DIR = RAW_DIR / "taiwanjobs"
MANIFEST_PATH = RAW_DIR / "taiwanjobs_manifest.json"


@dataclass(frozen=True)
class DistrictZip:
    district: str
    zipno: str


DISTRICT_ZIPCODES = [
    DistrictZip("板橋區", "220"),
    DistrictZip("三重區", "241"),
    DistrictZip("中和區", "235"),
    DistrictZip("永和區", "234"),
    DistrictZip("新莊區", "242"),
    DistrictZip("新店區", "231"),
    DistrictZip("樹林區", "238"),
    DistrictZip("鶯歌區", "239"),
    DistrictZip("三峽區", "237"),
    DistrictZip("淡水區", "251"),
    DistrictZip("汐止區", "221"),
    DistrictZip("瑞芳區", "224"),
    DistrictZip("土城區", "236"),
    DistrictZip("蘆洲區", "247"),
    DistrictZip("五股區", "248"),
    DistrictZip("泰山區", "243"),
    DistrictZip("林口區", "244"),
    DistrictZip("深坑區", "222"),
    DistrictZip("石碇區", "223"),
    DistrictZip("坪林區", "232"),
    DistrictZip("三芝區", "252"),
    DistrictZip("石門區", "253"),
    DistrictZip("八里區", "249"),
    DistrictZip("平溪區", "226"),
    DistrictZip("雙溪區", "227"),
    DistrictZip("貢寮區", "228"),
    DistrictZip("金山區", "208"),
    DistrictZip("萬里區", "207"),
    DistrictZip("烏來區", "233"),
]


def source_url(zipno: str, count: int) -> str:
    query = urlencode({"zipno": zipno, "count": count})
    return f"https://free.taiwanjobs.gov.tw/webservice_taipei/Webservice.ashx?{query}"


def main() -> int:
    TAIWANJOBS_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    for item in DISTRICT_ZIPCODES:
        filename = f"taiwanjobs_{item.zipno}_{item.district}.xml"
        target = TAIWANJOBS_DIR / filename
        url = source_url(item.zipno, 1000)
        print(f"DOWNLOAD {item.district} ({item.zipno}) -> {target}")
        urlretrieve(url, target)
        records.append(
            {
                **asdict(item),
                "url": url,
                "local_path": str(target.relative_to(PROJECT_ROOT)),
                "downloaded_at": datetime.now().isoformat(timespec="seconds"),
                "source": "勞動部勞動力發展署台灣就業通網站職缺清單 OpenData API",
                "limit": "API 每次查詢最多 1000 筆；本腳本以新北市各行政區 3 碼郵遞區號分區下載。",
            }
        )

    MANIFEST_PATH.write_text(
        json.dumps({"updated_at": datetime.now().isoformat(timespec="seconds"), "sources": records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
