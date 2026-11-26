"""Read-only, dependency-free PE import inspection for runtime research.

Reads import names from the Windows executable's data directory. No PE code
is executed and no files are written. The static table does not include every
DLL loaded dynamically by a running game.
"""

from __future__ import annotations

import mmap
from pathlib import Path
import struct


class PeInspectionError(ValueError):
    pass


def _unpack(data: mmap.mmap, format_: str, offset: int):
    length = struct.calcsize(format_)
    if offset < 0 or offset + length > len(data):
        raise PeInspectionError("PE field outside executable")
    return struct.unpack_from(format_, data, offset)


def _cstring(data: mmap.mmap, offset: int, limit: int = 512) -> str:
    if offset < 0 or offset >= len(data):
        raise PeInspectionError("PE string outside executable")
    end = data.find(b"\0", offset, min(len(data), offset + limit + 1))
    if end < 0:
        raise PeInspectionError("Unterminated or oversized PE string")
    try:
        return data[offset:end].decode("ascii")
    except UnicodeDecodeError as exc:
        raise PeInspectionError("Non-ASCII PE import name") from exc


def scan_imports(filename: Path) -> dict[str, list[str]]:
    """Return import-table DLLs and named/ordinal imports; no runtime claims."""
    with Path(filename).open("rb") as file:
        if file.seek(0, 2) == 0:
            raise PeInspectionError("Empty executable")
        file.seek(0)
        with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as data:
            if data[:2] != b"MZ":
                raise PeInspectionError("Not an MZ executable")
            (nt_offset,) = _unpack(data, "<I", 0x3C)
            if nt_offset > 32 * 1024 * 1024 or data[nt_offset:nt_offset + 4] != b"PE\0\0":
                raise PeInspectionError("Invalid PE signature")
            coff = nt_offset + 4
            (machine, sections, _, _, _, opt_size, _) = _unpack(data, "<HHIIIHH", coff)
            if sections > 96 or opt_size < 96:
                raise PeInspectionError("Invalid PE section count or optional header")
            optional = coff + 20
            (magic,) = _unpack(data, "<H", optional)
            if magic == 0x20B:
                pointer_size, directory_start = 8, optional + 112
            elif magic == 0x10B:
                pointer_size, directory_start = 4, optional + 96
            else:
                raise PeInspectionError("Unsupported PE optional header")
            if machine not in (0x8664, 0x14C) or (pointer_size == 8) != (machine == 0x8664):
                raise PeInspectionError("Unsupported or mismatched PE architecture")
            if directory_start + 16 > optional + opt_size:
                raise PeInspectionError("Truncated PE data directories")
            (size_headers,) = _unpack(data, "<I", optional + 60)
            (import_rva, import_size) = _unpack(data, "<II", directory_start + 8)
            section_table = optional + opt_size
            ranges = []
            for number in range(sections):
                offset = section_table + number * 40
                (virtual_size, virtual_addr, raw_size, raw_offset) = _unpack(data, "<IIII", offset + 8)
                if raw_size:
                    ranges.append((virtual_addr, virtual_addr + max(raw_size, virtual_size), raw_offset, raw_size))

            def map_rva(rva: int, size: int = 1) -> int:
                if rva < size_headers and rva + size <= len(data):
                    return rva
                for start, end, raw, raw_size in ranges:
                    if start <= rva and rva + size <= end and rva - start + size <= raw_size:
                        file_offset = raw + rva - start
                        if file_offset + size <= len(data):
                            return file_offset
                raise PeInspectionError(f"Unmapped PE RVA 0x{rva:x}")

            if not import_rva or not import_size:
                return {}
            if import_size > 1024 * 1024:
                raise PeInspectionError("Implausibly large PE import directory")
            imports: dict[str, list[str]] = {}
            for i in range(min(4096, import_size // 20)):
                descriptor = map_rva(import_rva + i * 20, 20)
                original, _, _, name_rva, first_thunk = _unpack(data, "<IIIII", descriptor)
                if not any((original, name_rva, first_thunk)):
                    return imports
                if not name_rva or not first_thunk:
                    raise PeInspectionError("Incomplete PE import descriptor")
                dll = _cstring(data, map_rva(name_rva)).lower()
                thunk_rva = original or first_thunk
                ordinal_mask = 1 << (pointer_size * 8 - 1)
                names = []
                for j in range(8192):
                    offset = map_rva(thunk_rva + j * pointer_size, pointer_size)
                    (value,) = _unpack(data, "<Q" if pointer_size == 8 else "<I", offset)
                    if not value:
                        break
                    if value & ordinal_mask:
                        names.append(f"#{value & 0xffff}")
                    else:
                        value_offset = map_rva(value, 3)
                        names.append(_cstring(data, value_offset + 2))
                else:
                    raise PeInspectionError("PE thunk table exceeds limit")
                if dll in imports:
                    imports[dll].extend(names)
                else:
                    imports[dll] = names
            raise PeInspectionError("PE import descriptors lack terminator")
