"""Manifest-allowlisted local methodology retrieval, separate from numeric data."""
import hashlib
import json
from pathlib import Path


class LocalKnowledgeSearch:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def search(self, query):
        query = query.lower().replace(" ", "")
        manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        matches = []
        for doc in manifest["documents"]:
            score = sum(term.lower().replace(" ", "") in query for term in doc["keywords"])
            if not score:
                continue
            path = (self.root / doc["path"]).resolve()
            if not path.is_relative_to(self.root) or path.suffix != ".md":
                raise ValueError("Invalid knowledge manifest path")
            content = path.read_bytes()
            if hashlib.sha256(content).hexdigest() != doc["sha256"]:
                raise ValueError("Knowledge document hash mismatch")
            matches.append({"document_id": doc["id"], "path": doc["path"],
                            "text": content.decode("utf-8"), "sha256": doc["sha256"],
                            "source_files": doc["source_files"], "score": score})
        return sorted(matches, key=lambda x: (-x["score"], x["document_id"]))[:3]
