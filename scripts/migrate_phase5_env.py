#!/usr/bin/env python3
"""Add the Phase 5 mTLS requirement to an existing private production env file.

This migration changes only MPC_REQUIRE_CLIENT_CERT. It does not rotate or
print application secrets and is safe to rerun.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path


def migrate(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Environment file not found: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    matches = [index for index, line in enumerate(lines) if line.strip().startswith("MPC_REQUIRE_CLIENT_CERT=")]
    if len(matches) > 1:
        raise ValueError("Duplicate MPC_REQUIRE_CLIENT_CERT entries; resolve them manually")

    if matches:
        index = matches[0]
        current = lines[index].split("=", 1)[1].strip().lower()
        if current == "true":
            return "already-enabled"
        lines[index] = "MPC_REQUIRE_CLIENT_CERT=true"
        result = "enabled"
    else:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("MPC_REQUIRE_CLIENT_CERT=true")
        result = "added"

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if os.name == "posix":
        path.chmod(0o600)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("env_file", nargs="?", default=".env.production")
    args = parser.parse_args()
    path = Path(args.env_file).expanduser().resolve()
    try:
        result = migrate(path)
    except (OSError, ValueError) as error:
        parser.exit(2, f"ERROR: {error}\n")
    messages = {
        "added": "Added MPC_REQUIRE_CLIENT_CERT=true without rotating any secrets.",
        "enabled": "Enabled MPC_REQUIRE_CLIENT_CERT=true without rotating any secrets.",
        "already-enabled": "MPC_REQUIRE_CLIENT_CERT is already enabled; no changes made.",
    }
    print(f"{messages[result]} File: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
