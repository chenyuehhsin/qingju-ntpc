from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEBSITE_DIR = PROJECT_ROOT / "website"
WEBSITE_DATA = WEBSITE_DIR / "data"
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_-]{20,}|OPENAI_API_KEY\s*=\s*([^\s`'\"]+)|password\s*[:=]\s*([^\s`'\"]+)|secret\s*[:=]\s*([^\s`'\"]+))", re.I)


def check(name: str, ok: bool, detail: str = "") -> tuple[str, bool, str]:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}{': ' + detail if detail else ''}")
    return name, ok, detail


def run(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=PROJECT_ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True, check=False)


def playwright_available() -> bool:
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if npx is None:
        return False
    return run([npx, "--no-install", "playwright", "--version"]).returncode == 0


def backend_health() -> str:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1.5) as response:
            return response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError):
        return "optional backend unavailable"


def secret_findings() -> list[str]:
    findings = []
    skip_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", "raw", "raw_snapshots", "staging"}
    suffixes = {".py", ".js", ".html", ".css", ".md", ".txt", ".json", ".yml", ".yaml", ".example", ""}
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file() or any(part in skip_dirs for part in path.parts):
            continue
        if path.suffix not in suffixes and path.name != ".env":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line in text.splitlines():
            if "SECRET_RE" in line:
                continue
            for match in SECRET_RE.finditer(line):
                value = match.group(0)
                if value.strip() == "OPENAI_API_KEY=":
                    continue
                findings.append(f"{path.relative_to(PROJECT_ROOT)}: {value[:32]}")
    return findings


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    results: list[tuple[str, bool, str]] = []
    required_resources = [
        "index.html",
        "app.js",
        "styles.css",
        "data/youth_employment_map.json",
        "data/youth_employment_history.json",
        "data/new_taipei_districts.geojson",
        "data/build_info.json",
    ]
    missing = [item for item in required_resources if not (WEBSITE_DIR / item).exists()]
    results.append(check("frontend resources available", not missing, ", ".join(missing)))

    payload = json.loads((WEBSITE_DATA / "youth_employment_map.json").read_text(encoding="utf-8"))
    records = payload.get("records", [])
    districts = [row.get("district") for row in records]
    results.append(check("29 districts", len(districts) == 29 and len(set(districts)) == 29, f"{len(set(districts))}/29"))
    results.append(check("JSON exists", (WEBSITE_DATA / "youth_employment_map.json").exists()))
    results.append(check("GeoJSON exists", (WEBSITE_DATA / "new_taipei_districts.geojson").exists()))

    history = json.loads((WEBSITE_DATA / "youth_employment_history.json").read_text(encoding="utf-8"))
    latest = history.get("latest_snapshot")
    latest_rows = [row for row in history.get("records", []) if row.get("snapshot_month") == latest]
    results.append(check("latest snapshot valid", latest == "2026-08" and len(latest_rows) == 29, str(latest)))
    first = latest_rows[0] if latest_rows else {}
    results.append(check("history manifest valid", history.get("history_manifest", {}).get("latest_period") == latest, str(history.get("history_manifest", {}).get("latest_period"))))
    results.append(check("temporal provenance", first.get("population_reference_month") == "2026-07" and bool(first.get("jobs_snapshot_as_of")), f"population={first.get('population_reference_month')}, jobs={first.get('jobs_snapshot_as_of')}"))

    df = pd.DataFrame(records)
    index_ok = "youth_employment_opportunity_index" in df and pd.to_numeric(df["youth_employment_opportunity_index"], errors="coerce").between(0, 100).all()
    reliability_ok = "index_reliability_score" in df and pd.to_numeric(df["index_reliability_score"], errors="coerce").between(0, 100).all()
    results.append(check("index valid", bool(index_ok)))
    results.append(check("reliability valid", bool(reliability_ok)))

    ai = run([sys.executable, "scripts/test_ai_decision_engine.py"])
    results.append(check("AI deterministic engine valid", ai.returncode == 0))
    fallback = run([sys.executable, "scripts/test_openai_fallback.py"])
    results.append(check("OpenAI fallback valid", fallback.returncode == 0))
    findings = secret_findings()
    results.append(check("no secret exposed", not findings, "; ".join(findings[:3])))
    results.append(check("backend health optional", True, backend_health()))

    size_info = {
        "json_kb": round((WEBSITE_DATA / "youth_employment_map.json").stat().st_size / 1024, 1),
        "geojson_kb": round((WEBSITE_DATA / "new_taipei_districts.geojson").stat().st_size / 1024, 1),
    }
    results.append(check("performance sanity", size_info["json_kb"] < 15000 and size_info["geojson_kb"] < 5000, json.dumps(size_info)))

    if playwright_available():
        npx = shutil.which("npx") or shutil.which("npx.cmd")
        e2e = run([npx, "playwright", "test"])
        results.append(check("browser E2E passed", e2e.returncode == 0))
    else:
        results.append(check("browser E2E passed", False, "Playwright is not installed"))

    failed = [name for name, ok, _detail in results if not ok]
    print("")
    if failed:
        print("DEMO NOT READY")
        print("Reasons: " + ", ".join(failed))
        return 1
    print("DEMO READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
