#!/usr/bin/env python3
"""Read-only inventory for an owned PC copy of Spider-Man: Miles Morales.

This is a research tool, NOT a game launcher or compatibility patch. It does
not change game files, access Steam credentials, or transmit any information.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import sys

TITLE = "Marvel's Spider-Man: Miles Morales"
STEAM_APP_ID = 1817190
EXECUTABLE = "MilesMorales.exe"
TOC = "asset_archive/toc"
MAX_FILES = 50000


class InspectionError(Exception):
    """Raised when a folder is not a safe, inspectable candidate."""


def sha256_file(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def machine_type(path: Path) -> str:
    """Read only the PE headers; never execute the supplied program."""
    with path.open("rb") as stream:
        if stream.read(2) != b"MZ":
            return "not-pe"
        stream.seek(0x3C)
        offset = stream.read(4)
        if len(offset) != 4:
            return "invalid-pe"
        pe_offset = struct.unpack("<I", offset)[0]
        if pe_offset < 0x40 or pe_offset > 32 * 1024 * 1024:
            return "invalid-pe"
        stream.seek(pe_offset)
        header = stream.read(6)
        if len(header) != 6 or header[:4] != b"PE\0\0":
            return "invalid-pe"
        arch = struct.unpack("<H", header[4:])[0]
        return {0x8664: "x86_64", 0x014C: "x86", 0xAA64: "arm64"}.get(arch, f"unknown-{arch:04x}")


def inspect(root: Path, hash_assets: bool = False) -> dict:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise InspectionError("The supplied game path is not a directory.")
    exe = root / EXECUTABLE
    toc = root / TOC
    if not exe.is_file() or not toc.is_file():
        raise InspectionError(f"Expected {EXECUTABLE} and {TOC} in the game folder.")
    if exe.is_symlink() or toc.is_symlink():
        raise InspectionError("The executable and archive index must not be symbolic links.")

    entries = []
    total_size = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(directory) / d).is_symlink())
        for name in sorted(files):
            path = Path(directory) / name
            if path.is_symlink() or not path.is_file():
                continue  # Never follow file links outside the selected game folder.
            relative = path.relative_to(root).as_posix()
            if len(entries) >= MAX_FILES:
                raise InspectionError(f"Too many files; limit is {MAX_FILES}.")
            size = path.stat().st_size
            total_size += size
            entry = {"path": relative, "size": size}
            if relative.lower() in {EXECUTABLE.lower(), TOC.lower()} or hash_assets:
                entry["sha256"] = sha256_file(path)
            entries.append(entry)

    return {
        "schema_version": 1,
        "title": TITLE,
        "steam_app_id": STEAM_APP_ID,
        "status": "research-only; NOT compatible or playable on Xbox",
        "executable": EXECUTABLE,
        "architecture": machine_type(exe),
        "file_count": len(entries),
        "total_bytes": total_size,
        "fully_hashed": hash_assets,
        "files": entries,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="Local folder containing your legitimately owned PC game")
    parser.add_argument("--output", type=Path, help="JSON output path (defaults to standard output)")
    parser.add_argument("--hash-assets", action="store_true", help="Hash every file; slow for large game archives")
    args = parser.parse_args(argv)
    try:
        result = inspect(args.folder, args.hash_assets)
        payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            output = args.output.expanduser().resolve()
            game_root = args.folder.expanduser().resolve()
            if output == game_root or game_root in output.parents:
                raise InspectionError("Refusing to write inside the original game folder.")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(payload, encoding="utf-8")
            print(f"Wrote a local research profile to {output}")
        else:
            print(payload, end="")
    except (InspectionError, OSError) as exc:
        print(f"Inspection failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
