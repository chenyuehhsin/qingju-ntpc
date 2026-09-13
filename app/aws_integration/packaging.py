"""Create a minimal container context from an explicit tracked-file allowlist."""
from pathlib import Path
import shutil
import subprocess
import hashlib
import json
from .config import Blocked


def package(root):
    root = Path(root).resolve()
    target = root / ".aws/build"
    target.mkdir(parents=True, exist_ok=True)
    # Read existing engine assets as bytes so source hashes match local parity.
    tracked = subprocess.check_output(["git", "ls-files", "-z", "app", "data/processed", "outputs", "knowledge_base", "data/data_catalog.csv", "requirements.txt"], cwd=root).decode().split("\0")
    extra = [p.relative_to(root).as_posix() for p in (root / "app/aws_integration").glob("*.py")]
    files = sorted(set([p for p in tracked if p] + extra + ["requirements-aws.txt"]))
    inventory = []
    for relative in files:
        source = (root / relative).resolve()
        if not source.is_relative_to(root) or source.is_symlink():
            raise Blocked("Invalid package path")
        dest = target / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        inventory.append({"path": relative, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
    # Remove nothing: stale context files cause a fail, never silently ship them.
    allowed = set(files) | {"Dockerfile", "package-manifest.json"}
    if any(p.relative_to(target).as_posix() not in allowed for p in target.rglob("*") if p.is_file()):
        raise Blocked("Unexpected stale build files; inspect context before reuse")
    # CloudShell currently uses Docker's vfs storage driver.  Keeping the
    # curated context in one COPY instruction avoids duplicating the whole
    # Lambda filesystem for every source directory on that driver.
    docker = '''FROM public.ecr.aws/lambda/python:3.13
COPY . ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-aws.txt
ENV PYTHONPATH=/var/task/app
CMD ["aws_integration.lambda_handler.handler"]
'''
    (target / "Dockerfile").write_text(docker, encoding="utf-8")
    (target / "package-manifest.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    return {"status": "LOCAL_CONTEXT_ONLY", "path": str(target), "files": len(files), "image_built": False, "deployed": False}
