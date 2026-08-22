#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

TOKEN_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
TEST_API_URL = "https://tdx.transportdata.tw/api/basic/v2/Basic/City"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def require_credentials() -> tuple[str, str]:
    load_dotenv(ENV_PATH)
    client_id = os.environ.get("TDX_CLIENT_ID", "").strip()
    client_secret = os.environ.get("TDX_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        print(
            "TDX credentials are not configured. Fill .env with TDX_CLIENT_ID and TDX_CLIENT_SECRET, then rerun.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return client_id, client_secret


def get_access_token(client_id: str, client_secret: str) -> str:
    payload = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))
    token = body.get("access_token")
    if not token:
        raise RuntimeError("TDX token response did not include access_token.")
    return token


def call_test_api(access_token: str) -> list[dict[str, object]]:
    request = urllib.request.Request(
        TEST_API_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "User-Agent": "qingju-ntpc-hackathon/0.1 (tdx connectivity test)",
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"TDX test API returned HTTP {response.status}")
        content_type = response.headers.get("Content-Type", "")
        body = response.read().decode("utf-8")
        if "application/json" not in content_type:
            raise RuntimeError(f"TDX test API returned non-JSON content type: {content_type}")
        return json.loads(body)


def main() -> int:
    client_id, client_secret = require_credentials()
    try:
        token = get_access_token(client_id, client_secret)
        data = call_test_api(token)
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        print(f"TDX API test failed with HTTP {exc.code}: {message[:500]}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"TDX API test failed due to network error: {exc.reason}", file=sys.stderr)
        return 1

    print("TDX authentication succeeded.")
    print(f"TDX test API succeeded: received {len(data) if isinstance(data, list) else 'non-list'} JSON records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
