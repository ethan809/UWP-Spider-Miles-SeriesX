"""Source-layout safety checks; these do not compile or exercise Xbox/Steam."""

import pathlib
import re
import unittest
import xml.etree.ElementTree as ET


ROOT = pathlib.Path(__file__).resolve().parents[1]


def source(name):
    return (ROOT / "source" / name).read_text(encoding="utf-8")


class MilesSteamSourceChecks(unittest.TestCase):
    def test_xaml_is_well_formed_and_selection_handler_exists(self):
        root = ET.parse(ROOT / "source" / "MainPage.xaml").getroot()
        names = {item.attrib.get("{http://schemas.microsoft.com/winfx/2006/xaml}Name")
                 for item in root.iter()}
        self.assertIn("SteamGameList", names)
        self.assertIn("SteamGame_Changed", source("MainPage.xaml.cs"))

    def test_miles_uses_separate_owned_app_and_base_depots(self):
        session = source("SteamTransfer/SteamSession.cs")
        self.assertRegex(session, r"MilesAppId\s*=\s*1817190\s*;")
        self.assertRegex(session, r"RemasteredAppId\s*=\s*1817070\s*;")
        plan = session.split("Task<List<TransferFile>> ReadMilesPlan", 1)[1]
        ids = re.search(r"uint\[\]\s+depots\s*=\s*\{([^}]+)\}", plan)
        self.assertIsNotNone(ids)
        self.assertEqual([int(part.strip()) for part in ids.group(1).split(",")],
                         [1817191, 1817192, 1817194])
        self.assertIn('planned.ContainsKey("MilesMorales.exe")', plan)
        self.assertIn("entry.FileHash.Length != 20", plan)
        self.assertIn("transfer.Validate()", plan)

    def test_download_only_storage_and_ui_warning(self):
        downloader = source("SteamDownload.cs")
        ui = source("MainPage.xaml.cs")
        self.assertIn('Path.Combine(localFolder, "MilesMoralesSteam")', downloader)
        self.assertIn("session.ReadMilesPlan(token)", downloader)
        self.assertIn("RunMilesAsync", downloader)
        self.assertIn("ConfirmMilesDownload()", ui)
        self.assertIn("NOT playable on Xbox", ui)
        self.assertIn("SteamDownload.RunMilesAsync", ui)
        self.assertIn("SteamDownload.RunAsync", ui)

    def test_steam_sha1_does_not_remove_remastered_sha256(self):
        transfer = source("SteamTransfer/TransferCore.cs")
        self.assertIn("(Expected.Hash.Length != 64 && Expected.Hash.Length != 40)", transfer)
        self.assertIn("SHA1.Create()", transfer)
        self.assertIn("SHA256.Create()", transfer)
        self.assertIn("expected.Hash.Length == 40", transfer)


if __name__ == "__main__":
    unittest.main()
