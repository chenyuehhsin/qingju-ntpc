from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
import os


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_step(name: str, command: list[str], *, required: bool = True) -> tuple[str, bool]:
    print(f"\n== {name} ==")
    env = os.environ.copy()
    env.pop("FORCE_COLOR", None)
    env.pop("NO_COLOR", None)
    completed = subprocess.run(command, cwd=PROJECT_ROOT, env=env, text=True, encoding="utf-8", errors="replace", capture_output=True, check=False)
    if completed.stdout:
        print(completed.stdout)
    if completed.stderr:
        print(completed.stderr)
    ok = completed.returncode == 0
    print(("PASS" if ok else "FAIL") + f" {name}")
    return name, ok or not required


def playwright_available() -> bool:
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if npx is None:
        return False
    env = os.environ.copy()
    env.pop("FORCE_COLOR", None)
    env.pop("NO_COLOR", None)
    completed = subprocess.run([npx, "--no-install", "playwright", "--version"], cwd=PROJECT_ROOT, env=env, text=True, encoding="utf-8", errors="replace", capture_output=True, check=False)
    return completed.returncode == 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    python_files = [
        "src/config.py",
        "src/sources/base.py",
        "src/sources/population_source.py",
        "src/sources/taiwanjobs_source.py",
        "src/ai_decision_engine.py",
        "server/app.py",
        "server/ai_service.py",
        "scripts/run_demo.py",
        "scripts/demo_preflight.py",
        "scripts/validate_all.py",
        "scripts/run_monthly_pipeline.py",
        "scripts/test_monthly_pipeline.py",
        "src/policy_assistant.py",
        "scripts/test_policy_assistant.py",
    ]
    steps: list[tuple[str, bool]] = []
    steps.append(run_step("data validation", [sys.executable, "scripts/validate_youth_employment_data.py"]))
    steps.append(run_step("history validation", [sys.executable, "scripts/validate_historical_data.py"]))
    steps.append(run_step("AI deterministic tests", [sys.executable, "scripts/test_ai_decision_engine.py"]))
    steps.append(run_step("Policy assistant tests", [sys.executable, "scripts/test_policy_assistant.py"]))
    steps.append(run_step("Policy catalog freshness", [sys.executable, "scripts/export_policy_catalog.py", "--check"]))
    steps.append(run_step("trend tests", [sys.executable, "scripts/test_trend_pipeline.py"]))
    steps.append(run_step("monthly pipeline tests", [sys.executable, "scripts/test_monthly_pipeline.py"]))
    steps.append(run_step("write build info", [sys.executable, "scripts/write_build_info.py"]))
    steps.append(run_step("Python compile check", [sys.executable, "-m", "py_compile", *python_files]))
    steps.append(run_step("JavaScript syntax check", ["node", "--check", "website/app.js"]))
    steps.append(run_step("Policy JavaScript syntax check", ["node", "--check", "website/policy-assistant.js"]))
    if playwright_available():
        npx = shutil.which("npx") or shutil.which("npx.cmd")
        steps.append(run_step("Playwright E2E", [npx, "playwright", "test"]))
    else:
        print("\n== Playwright E2E ==\nSKIP Playwright E2E: Playwright is not installed. Run `npm install` and `npx playwright install chromium`.")
        steps.append(("Playwright E2E", True))

    failed = [name for name, ok in steps if not ok]
    print("\n== Summary ==")
    for name, ok in steps:
        print(("PASS" if ok else "FAIL") + f" {name}")
    if failed:
        print(f"VALIDATION FAILED: {', '.join(failed)}")
        return 1
    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
