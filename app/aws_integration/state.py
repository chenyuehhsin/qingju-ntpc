"""Atomic allowlisted state. Never store arbitrary AWS responses or credentials."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
from .config import Blocked


class State:
    def __init__(self, path, region, account):
        self.path = Path(path)
        self.data = {"version": 1, "region": region, "account": account, "resources": {}, "ingestions": {}}
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
            self.validate()
            if self.data.get("region") != region or self.data.get("account") != account:
                raise Blocked("State belongs to another region/account; refusing reuse")

    @contextmanager
    def locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.path.with_suffix(".lock")
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise Blocked("Another deployment holds state lock; inspect before removing stale lock") from None
        os.close(fd)
        try:
            yield self
        finally:
            lock.unlink()

    def save(self):
        self.validate()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)

    def validate(self):
        if set(self.data) != {"version", "region", "account", "resources", "ingestions"}:
            raise Blocked("Unexpected state fields; refusing to persist secrets or arbitrary responses")
        for resource in self.data["resources"].values():
            if set(resource) != {"id", "arn", "created", "fingerprint"}:
                raise Blocked("Unexpected resource state fields")

    def record(self, key, identifier, arn="", created=False, fingerprint=""):
        old = self.data["resources"].get(key, {})
        if old and old["id"] != identifier:
            raise Blocked("Resource identity conflict: " + key)
        self.data["resources"][key] = {"id": identifier, "arn": arn, "created": old.get("created", created), "fingerprint": fingerprint}
        self.save()

    def get(self, key):
        return self.data["resources"].get(key, {}).get("id")
