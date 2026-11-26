import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from inspect_miles import InspectionError, inspect, main  # noqa: E402


class MilesProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "game"
        (self.root / "asset_archive").mkdir(parents=True)
        header = bytearray(128)
        header[:2] = b"MZ"
        struct.pack_into("<I", header, 0x3C, 0x40)
        header[0x40:0x44] = b"PE\0\0"
        struct.pack_into("<H", header, 0x44, 0x8664)
        (self.root / "MilesMorales.exe").write_bytes(header)
        (self.root / "asset_archive" / "toc").write_bytes(b"asset index")

    def test_detects_candidate_and_hashes_critical_files(self):
        result = inspect(self.root)
        self.assertEqual(result["steam_app_id"], 1817190)
        self.assertEqual(result["architecture"], "x86_64")
        self.assertIn("NOT compatible", result["status"])
        self.assertEqual(result["file_count"], 2)
        self.assertFalse(result["fully_hashed"])
        file_map = {file["path"]: file for file in result["files"]}
        self.assertEqual(file_map["asset_archive/toc"]["sha256"], hashlib.sha256(b"asset index").hexdigest())

    def test_missing_toc_rejected(self):
        (self.root / "asset_archive" / "toc").unlink()
        with self.assertRaises(InspectionError):
            inspect(self.root)

    def test_hash_assets_is_opt_in(self):
        (self.root / "cache.pso").write_bytes(b"shader cache")
        only_critical = inspect(self.root)
        full = inspect(self.root, hash_assets=True)
        self.assertNotIn("sha256", next(f for f in only_critical["files"] if f["path"] == "cache.pso"))
        self.assertIn("sha256", next(f for f in full["files"] if f["path"] == "cache.pso"))

    def test_refuses_writing_inside_game_folder(self):
        result = main([str(self.root), "--output", str(self.root / "report.json")])
        self.assertEqual(result, 1)
        self.assertFalse((self.root / "report.json").exists())

    def test_symlinked_file_is_not_read(self):
        external = Path(self.temp.name) / "outside"
        external.write_text("private")
        (self.root / "linked.dat").symlink_to(external)
        result = inspect(self.root)
        self.assertEqual(result["file_count"], 2)

    def test_launcher_import_paths_explicitly_reject_miles(self):
        """Static regression guard; this does not compile or execute the UWP app."""
        source = Path(__file__).resolve().parents[1] / "source"
        versions = (source / "GameVersionSupport.cs").read_text()
        self.assertIn('MilesExecutable="MilesMorales.exe"', versions)
        self.assertIn("MilesNotReadyMessage", versions)
        self.assertIn("RejectMilesMorales", versions)
        for filename in ("ImportEngine.cs", "WifiFolderTransfer.cs"):
            contents = (source / filename).read_text()
            self.assertIn("GameVersionSupport.RejectMilesMorales", contents)
        folder = (source / "FolderImportEngine.cs").read_text()
        self.assertIn("CheckForMilesMorales", folder)
        self.assertIn("catch(FileNotFoundException)", folder)


if __name__ == "__main__":
    unittest.main()
