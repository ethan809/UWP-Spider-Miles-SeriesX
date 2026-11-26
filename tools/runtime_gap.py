#!/usr/bin/env python3
"""Compare static PC-game imports to a claimed Xbox runtime export inventory.

This tool does not execute Windows games. An empty gap report means only that
the declared import names match; runtime behavior, DX12, memory, DRM and
dynamic imports still require live validation on the Xbox.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def compare(profile: dict, runtime: dict) -> dict:
    required = profile.get("static_imports")
    available = runtime.get("exported_functions")
    if not isinstance(required, dict) or not isinstance(available, dict):
        raise ValueError("Expected static_imports and exported_functions mappings")
    supported = {
        str(dll).lower(): {str(name).lower() for name in names}
        for dll, names in available.items()
        if isinstance(names, list)
    }
    missing = {}
    total = 0
    matched = 0
    for dll, names in sorted(required.items()):
        if not isinstance(names, list):
            raise ValueError(f"Invalid import list for {dll}")
        got = supported.get(dll.lower(), set())
        absent = sorted({name for name in names if name.lower() not in got})
        if absent:
            missing[dll] = absent
        total += len(names)
        matched += len(names) - len(absent)
    return {
        "status": "static-import-name comparison only; NOT Xbox playability proof",
        "required_import_count": total,
        "matched_import_count": matched,
        "missing_imports": missing,
        "all_static_import_names_matched": not missing,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game_profile", type=Path, help="Local output from inspect_miles.py")
    parser.add_argument("runtime_exports", type=Path, help="Audited JSON mapping: {exported_functions: {dll: [name, ...]}}")
    args = parser.parse_args(argv)
    try:
        game = json.loads(args.game_profile.read_text(encoding="utf-8"))
        runtime = json.loads(args.runtime_exports.read_text(encoding="utf-8"))
        print(json.dumps(compare(game, runtime), indent=2, sort_keys=True))
    except (ValueError, OSError) as exc:
        print(f"Runtime comparison failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
