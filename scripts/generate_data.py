#!/usr/bin/env python3
"""Generate sample data files under data/ for the update-repodata workflow."""

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / "data" / "repodata.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--noop",
        action="store_true",
        help="deterministic output (fixed timestamp and seed) so re-runs produce no diff",
    )
    args = parser.parse_args()

    if args.noop:
        rng = random.Random(0)
        generated_at = "1970-01-01T00:00:00+00:00"
    else:
        rng = random.Random()
        generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    records = [
        {"id": i, "name": f"item-{i}", "value": rng.randint(0, 1000)}
        for i in range(1, 6)
    ]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps({"generated_at": generated_at, "records": records}, indent=2) + "\n"
    )
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
