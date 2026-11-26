from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from pe_imports import PeInspectionError, scan_imports  # noqa: E402


def fake_pe64() -> bytes:
    """Minimal synthetic PE64 with one D3D12 import and no executable code."""
    content = bytearray(1024)
    content[:2] = b"MZ"
    struct.pack_into("<I", content, 0x3C, 0x80)
    content[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", content, 0x84, 0x8664, 1, 0, 0, 0, 240, 0)
    struct.pack_into("<H", content, 0x98, 0x20B)
    struct.pack_into("<I", content, 0x98 + 60, 0x200)  # SizeOfHeaders
    struct.pack_into("<II", content, 0x98 + 112 + 8, 0x1000, 40)
    section = 0x98 + 240
    content[section:section + 8] = b".rdata\0\0"
    struct.pack_into("<IIII", content, section + 8, 0x200, 0x1000, 0x200, 0x200)
    struct.pack_into("<IIIII", content, 0x200, 0x1070, 0, 0, 0x1050, 0x1070)
    content[0x250:0x25A] = b"d3d12.dll\0"
    struct.pack_into("<Q", content, 0x270, 0x1090)
    content[0x290:0x292] = b"\0\0"  # IMAGE_IMPORT_BY_NAME hint
    content[0x292:0x2A5] = b"D3D12CreateDevice\0"
    return bytes(content)


class ImportScannerTests(unittest.TestCase):
    def test_reads_named_d3d12_import_without_running_it(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "MilesMorales.exe"
            file.write_bytes(fake_pe64())
            self.assertEqual(scan_imports(file), {"d3d12.dll": ["D3D12CreateDevice"]})

    def test_rejects_malformed_binary(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "corrupt.exe"
            file.write_bytes(b"Not an executable")
            with self.assertRaises(PeInspectionError):
                scan_imports(file)

    def test_empty_imports_still_parse(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "empty.exe"
            binary = bytearray(fake_pe64())
            struct.pack_into("<II", binary, 0x98 + 112 + 8, 0, 0)
            file.write_bytes(binary)
            self.assertEqual(scan_imports(file), {})


if __name__ == "__main__":
    unittest.main()
