"""Whole manifest verification before any upload. No repository-wide upload."""
import hashlib
import json
from pathlib import Path
import re
from .config import Blocked

SECRETS = re.compile(rb"(?:AKIA|ASIA)[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:aws_secret_access_key|aws_session_token)\s*[:=]\s*\S+", re.I)
ALLOWED = {"methodology", "definitions", "data_catalog", "limitations"}


def documents(root):
    root = Path(root).resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    result, paths = [], set()
    for entry in manifest["documents"]:
        relative = Path(entry["path"])
        path = (root / relative).resolve()
        if relative.as_posix() in paths or not path.is_relative_to(root) or relative.parts[0] not in ALLOWED or path.suffix != ".md":
            raise Blocked("Invalid or duplicate KB manifest entry")
        paths.add(relative.as_posix())
        body = path.read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        if digest != entry["sha256"] or SECRETS.search(body):
            raise Blocked("KB integrity/secret validation failed: " + relative.as_posix())
        result.append({"path": relative.as_posix(), "body": body, "sha256": digest, "id": entry["id"],
                       "category": relative.parts[0], "sources": entry["source_files"]})
    if not result:
        raise Blocked("Empty KB manifest")
    return result


def manifest_digest(docs):
    return hashlib.sha256(json.dumps([(d["path"], d["sha256"]) for d in docs], sort_keys=True).encode()).hexdigest()
