"""Synthetic log tests only; no actual Miles Morales boot is claimed."""

import importlib.util
import io
import pathlib
import unittest


PATH = pathlib.Path(__file__).resolve().parents[1] / "tools" / "miles_boot_report.py"
SPEC = importlib.util.spec_from_file_location("miles_boot_report", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MilesBootReportTests(unittest.TestCase):
    def test_unrelated_selftest_cannot_prove_miles_launched(self):
        report = MODULE.analyze([
            "trt: launching S:\\Program Files\\guest_hello.exe (3072 bytes)",
            "trt: MAPPED base=1234 size=5000 entry=1000",
            "trt: SEALED (W^X: code pages now RX)",
        ])
        self.assertFalse(report["target_launch_observed"])
        self.assertFalse(report["pe_mapped"])

    def test_mapped_miles_is_not_reported_as_booted(self):
        report = MODULE.analyze(io.StringIO(
            "trt: launching Q:\\Games\\Miles\\MilesMorales.exe (123456 bytes)\n"
            "trt: MAPPED base=1234 preferred=140000000 size=500000 entry=1000\n"
            "trt: SEALED (W^X: code pages now RX)\n"
            "guest fault [main] caller 1: MilesMorales.exe+0x120\n"
        ))
        self.assertTrue(report["target_launch_observed"])
        self.assertTrue(report["pe_mapped"])
        self.assertTrue(report["pe_sealed"])
        self.assertFalse(report["boot_verified"])
        self.assertIn("guest exception or fault", report["possible_blockers"])

    def test_only_miles_session_counts_and_no_raw_paths_leak(self):
        report = MODULE.analyze([
            "trt: launching Q:\\Games\\Miles\\MilesMorales.exe (1 bytes)",
            "trt: MAPPED base=1234",
            "d3d12: D3D12CreateDevice -> FAILED",
            "trt: launching Q:\\Games\\Other\\Other.exe (2 bytes)",
            "dxgi: presented frame=1",  # Belongs to Other, not Miles.
        ])
        self.assertTrue(report["d3d12_call_observed"])
        self.assertFalse(report["frame_presentation_log_observed"])
        self.assertIn("DirectX 12 initialization failure", report["possible_blockers"])
        self.assertNotIn("Q:", str(report))
        self.assertFalse(report["boot_verified"])

    def test_missing_file_error_is_named_without_file_path(self):
        report = MODULE.analyze([
            "trt: launching MilesMorales.exe (100 bytes)",
            "kernel32: CreateFileW open failed on host",
            "  host: Q:/Users/PRIVATE/Packages/games/secret.asset",
        ])
        self.assertEqual(report["possible_blockers"], ["game file read failure"])
        self.assertNotIn("secret.asset", str(report))


if __name__ == "__main__":
    unittest.main()
