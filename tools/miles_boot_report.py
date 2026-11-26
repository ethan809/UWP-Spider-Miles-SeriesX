#!/usr/bin/env python3
"""Summarize a *real* Tiramisu Miles Morales console log without sharing it.

This is a boot-evidence reader, not a launcher, emulator, or compatibility fix.
It deliberately never interprets a mapped PE as proof that a game booted.
"""

import argparse
import json
import pathlib
import re
import sys


LAUNCH = re.compile(r"\btrt:\s*launching\s+(.+?\.exe)\s*\(", re.IGNORECASE)
MILES = re.compile(r"(?:^|[\\/])MilesMorales\.exe$", re.IGNORECASE)


def analyze(lines):
    """Accept an iterable of log lines and report only title-scoped evidence."""
    active = False
    seen = False
    mapped = sealed = d3d12 = presented = False
    blockers = []
    matched_lines = 0

    def blocker(category):
        if category not in blockers:
            blockers.append(category)

    for raw_line in lines:
        line = raw_line.strip()
        match = LAUNCH.search(line)
        if match:
            target = match.group(1).strip().strip('"')
            is_miles = MILES.search(target) is not None
            if not is_miles and active:
                # A later game starts: never mix its successes with Miles.
                break
            if is_miles:
                seen = active = True
            continue
        if not active:
            continue
        matched_lines += 1
        folded = line.casefold()
        if "trt: mapped " in folded:
            mapped = True
        if "trt: sealed" in folded:
            sealed = True
        if "d3d12:" in folded or "d3d12createdevice" in folded:
            d3d12 = True
        if ("d3d12:" in folded or "dxgi:" in folded) and (
            "present frame=" in folded or "presented frame=" in folded
        ):
            presented = True
        if "fail import" in folded or "trt_err_import" in folded:
            blocker("import binding failure")
        if "guest fault" in folded or "unhandled guest exception" in folded:
            blocker("guest exception or fault")
        if "memory budget" in folded and ("refused" in folded or "exceeded" in folded):
            blocker("memory budget exceeded")
        if "createfilew open failed on host" in folded:
            blocker("game file read failure")
        if "d3d12" in folded and ("failed" in folded or "error" in folded):
            blocker("DirectX 12 initialization failure")

    return {
        "game": "Marvel's Spider-Man: Miles Morales",
        "runtime": "Tiramisu (external, unverified on this title)",
        "target_launch_observed": seen,
        "pe_mapped": mapped,
        "pe_sealed": sealed,
        "d3d12_call_observed": d3d12,
        "frame_presentation_log_observed": presented,
        "possible_blockers": blockers,
        "title_scoped_log_lines": matched_lines,
        "boot_verified": False,
        "note": "This report is log evidence only. A successful boot requires console video/input proof; no game files or raw logs are included.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=pathlib.Path, help="Exported real Tiramisu log as text")
    args = parser.parse_args(argv)
    try:
        if not args.log.is_file():
            raise OSError("Log file does not exist")
        if args.log.stat().st_size > 64 * 1024 * 1024:
            raise ValueError("Log is larger than the 64 MiB analysis limit")
        with args.log.open("r", encoding="utf-8", errors="replace") as handle:
            report = analyze(handle)
    except (OSError, ValueError) as exc:
        print(f"Cannot inspect log: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["target_launch_observed"] else 1


if __name__ == "__main__":
    sys.exit(main())
