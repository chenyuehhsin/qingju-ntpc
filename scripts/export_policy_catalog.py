"""Export only deterministic evidence, never raw jobs; --check detects stale exports."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.policy_assistant import build_catalog


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = ROOT / "website/data/policy_catalog.json"
    content = json.dumps(build_catalog(), ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.check:
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            raise SystemExit("Policy catalog stale: run python scripts/export_policy_catalog.py")
        print("PASS policy catalog matches official data, methodology and provenance")
    else:
        path.write_text(content, encoding="utf-8")
        print("Exported website/data/policy_catalog.json")


if __name__ == "__main__":
    main()
