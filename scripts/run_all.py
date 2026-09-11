#!/usr/bin/env python3
"""Run every hourly automation in this repo. Add new scripts here as they are created."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

JOBS = [
    [PY, str(ROOT / "scripts" / "robinhood_trending_crypto.py"), "--top", "15"],
]


def main() -> int:
    failed = 0
    for cmd in JOBS:
        print(f"\n=== {' '.join(cmd)} ===")
        r = subprocess.run(cmd, cwd=ROOT)
        if r.returncode != 0:
            failed += 1
            print(f"FAILED ({r.returncode}): {cmd}", file=sys.stderr)
    print(f"\nDone: {len(JOBS) - failed}/{len(JOBS)} succeeded.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
