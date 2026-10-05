"""Manual release inputs select an exact, independently labelled source bundle."""
import hashlib
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class SourceSelectionTests(unittest.TestCase):
    def select(self, directory, version):
        return subprocess.run([
            sys.executable, str(ROOT / "ffmpeg/package.py"), "select",
            directory, version,
        ], check=False, capture_output=True, text=True, timeout=180)

    def test_only_upstream_release_numbers_are_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            for version in ("master", "n7.1.5", "../7.1.5", "7.1.5;echo injected"):
                with self.subTest(version=version):
                    result = self.select(directory, version)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("Invalid FFmpeg release version", result.stderr)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_selected_version_changes_only_ffmpeg_and_includes_verified_source(self):
        original = json.loads((ROOT / "ffmpeg/sources.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            result = self.select(directory, "7.1.4")
            self.assertEqual(result.returncode, 0, result.stderr)
            selected = json.loads((Path(directory) / "sources.json").read_text())
            self.assertEqual(selected["ffmpeg"]["version"], "7.1.4")
            self.assertEqual(selected["ffmpeg"]["directory"], "ffmpeg-7.1.4")
            self.assertEqual(selected["ffmpeg"]["url"], "https://ffmpeg.org/releases/ffmpeg-7.1.4.tar.xz")
            for component in ("aom", "vpx", "zlib"):
                self.assertEqual(selected[component], original[component])
            for component in selected.values():
                archive = Path(directory) / component["archive"]
                with archive.open("rb") as stream:
                    self.assertEqual(hashlib.file_digest(stream, "sha256").hexdigest(),
                                     component["sha256"])
            with tarfile.open(Path(directory) / selected["ffmpeg"]["archive"]) as bundle:
                self.assertIn("ffmpeg-7.1.4/configure", bundle.getnames())


if __name__ == "__main__":
    unittest.main()
