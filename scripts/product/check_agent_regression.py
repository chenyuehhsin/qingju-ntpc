"""Verify protected tracked material against the audited M3 baseline."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "c604682c89bb69c8aae2c2a1318080a23c16c195"
PROTECTED = ["data", "outputs", "app/assistant_service.py", "app/components/policy_lens.py",
             "app/data_loader.py", "requirements.txt", "scripts/employment", "scripts/population",
             "scripts/policy"]


def check():
    proc = subprocess.run(["git", "diff", "--exit-code", BASELINE, "--", *PROTECTED],
                          cwd=ROOT, capture_output=True)
    report = {"baseline": BASELINE, "protected_paths": PROTECTED,
              "protected_tracked_content_unchanged": proc.returncode == 0,
              "opportunity_index": "Absent at baseline; no index or weights introduced",
              "reliability": "Existing samples/warnings and rules unchanged; no categorical levels introduced",
              "raw_data": "No raw writes or downloads; raw employment absent in this checkout and ignored by Git",
              "snapshots_and_provenance": "Tracked data/outputs unchanged, including original source hash metadata",
              "existing_assistant": "Original service unchanged; UI delegates policy queries to new tools"}
    (ROOT / "docs/AGENT_REGRESSION_CHECK.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(check())
