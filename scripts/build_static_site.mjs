import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

const root = process.cwd();
const source = path.join(root, "website");
const destination = path.join(root, "dist");
// Never deploy stale policy evidence after data or methodology changes.
execFileSync(process.env.PYTHON || "python", ["scripts/export_policy_catalog.py", "--check"], { stdio: "inherit" });

if (!fs.existsSync(path.join(source, "index.html"))) {
  throw new Error("Missing website/index.html");
}

fs.rmSync(destination, { recursive: true, force: true });
fs.mkdirSync(destination, { recursive: true });
fs.cpSync(source, destination, {
  recursive: true,
  filter: (src) => path.basename(src) !== ".server.pid",
});

console.log(`Built static site at ${destination}`);
