from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEBSITE_DIR = PROJECT_ROOT / "website"
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "8080"))
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def http_json(url: str, timeout: float = 2.0) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def check_dependencies() -> list[str]:
    missing = []
    for module in ["pandas", "fastapi", "uvicorn"]:
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(module)
    return missing


def check_data() -> None:
    required = [
        WEBSITE_DIR / "index.html",
        WEBSITE_DIR / "app.js",
        WEBSITE_DIR / "styles.css",
        WEBSITE_DIR / "data" / "youth_employment_map.json",
        WEBSITE_DIR / "data" / "youth_employment_history.json",
        WEBSITE_DIR / "data" / "new_taipei_districts.geojson",
    ]
    missing = [str(path.relative_to(PROJECT_ROOT)) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"Missing required demo files: {missing}")
    payload = json.loads((WEBSITE_DIR / "data" / "youth_employment_map.json").read_text(encoding="utf-8"))
    districts = [row.get("district") for row in payload.get("records", [])]
    if len(districts) != 29 or len(set(districts)) != 29:
        raise SystemExit("Demo data must contain exactly 29 New Taipei districts.")


def start_process(command: list[str], *, env: dict[str, str]) -> subprocess.Popen | None:
    return subprocess.Popen(command, cwd=PROJECT_ROOT, env=env)


def main() -> int:
    env = os.environ.copy()
    env.setdefault("DEMO_MODE", "1")
    missing = check_dependencies()
    if missing:
        raise SystemExit(f"Missing Python dependencies: {missing}. Run `pip install -r requirements.txt`.")
    check_data()
    subprocess.run([sys.executable, "scripts/write_build_info.py"], cwd=PROJECT_ROOT, check=False)

    processes: list[subprocess.Popen] = []
    if port_open(FRONTEND_PORT):
        print(f"Frontend already running: http://localhost:{FRONTEND_PORT}")
    else:
        processes.append(start_process([sys.executable, "-m", "http.server", str(FRONTEND_PORT), "--directory", "website"], env=env))
        print(f"Frontend: http://localhost:{FRONTEND_PORT}")

    backend_started = False
    if port_open(BACKEND_PORT):
        print(f"Backend already running: http://localhost:{BACKEND_PORT}")
    else:
        processes.append(start_process([sys.executable, "-m", "uvicorn", "server.app:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)], env=env))
        backend_started = True
        print(f"Backend: http://localhost:{BACKEND_PORT}")

    time.sleep(1.5 if backend_started else 0.2)
    health = http_json(f"http://127.0.0.1:{BACKEND_PORT}/health")
    print("")
    print(f"DEMO_MODE: {env.get('DEMO_MODE')}")
    print(f"OpenAI explanation: {'enabled' if env.get('OPENAI_API_KEY') else 'disabled'}")
    print("Deterministic assistant: enabled")
    print(f"Backend health: {health or 'unavailable'}")
    print("")
    print("Open this URL for the competition demo:")
    print(f"http://localhost:{FRONTEND_PORT}")
    print("")
    print("Press Ctrl+C to stop servers started by this script.")

    try:
        while True:
            live_processes = [process for process in processes if process and process.poll() is None]
            if not live_processes and processes:
                return 1
            time.sleep(1)
    except KeyboardInterrupt:
        for process in processes:
            if process and process.poll() is None:
                process.terminate()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
