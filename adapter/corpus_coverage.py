#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Render declared RewardHackBench corpus coverage from the adapter manifest."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from build import Entry, load_manifest


def coverage(entries: list[Entry]) -> dict[str, Any]:
    families: dict[str, list[Entry]] = defaultdict(list)
    for entry in entries:
        if entry.metadata:
            families[entry.metadata["source_task"]].append(entry)

    return {
        "families": [
            {
                "source_task": source_task,
                "hack_axes": sorted({entry.metadata["hack_axis"] for entry in family}),
                "cheat_modes": sorted(
                    {entry.metadata["cheat_mode"] for entry in family}
                ),
                "fixtures": [
                    {
                        "target_name": entry.target_name,
                        **entry.metadata,
                    }
                    for entry in sorted(family, key=lambda item: item.target_name)
                ],
            }
            for source_task, family in sorted(families.items())
        ]
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("adapter/manifest.yaml"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rendered = json.dumps(coverage(load_manifest(args.manifest)), indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
