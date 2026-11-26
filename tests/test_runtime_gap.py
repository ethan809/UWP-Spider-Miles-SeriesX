from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from runtime_gap import compare  # noqa: E402


class RuntimeComparisonTests(unittest.TestCase):
    def test_reports_missing_d3d12_import(self):
        profile = {"static_imports": {"D3D12.dll": ["D3D12CreateDevice", "D3D12SerializeRootSignature"]}}
        runtime = {"exported_functions": {"d3d12.dll": ["d3d12createdevice"]}}
        report = compare(profile, runtime)
        self.assertEqual(report["required_import_count"], 2)
        self.assertEqual(report["matched_import_count"], 1)
        self.assertEqual(report["missing_imports"], {"D3D12.dll": ["D3D12SerializeRootSignature"]})
        self.assertFalse(report["all_static_import_names_matched"])

    def test_matching_imports_are_not_claimed_to_be_playable(self):
        report = compare({"static_imports": {"KERNEL32.dll": ["HeapAlloc"]}},
                         {"exported_functions": {"kernel32.dll": ["heapalloc"]}})
        self.assertTrue(report["all_static_import_names_matched"])
        self.assertIn("NOT Xbox playability proof", report["status"])

    def test_malformed_inputs_rejected(self):
        with self.assertRaises(ValueError):
            compare({"static_imports": {"dxgi.dll": ["CreateDXGIFactory"]}}, {})


if __name__ == "__main__":
    unittest.main()
