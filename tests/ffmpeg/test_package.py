"""Certification of the download archive, including compliance and integrity."""
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class PackageTests(unittest.TestCase):
    def test_verified_download_contains_rebuildable_relocatable_tool(self):
        archive = Path(os.environ["NOVELTEA_FFMPEG_ARCHIVE"])
        expected, name = Path(str(archive) + ".sha256").read_text().strip().split("  ")
        self.assertEqual(name, archive.name)
        self.assertEqual(digest(archive), expected)
        with tempfile.TemporaryDirectory(prefix="noveltea extracted ") as directory:
            root = Path(directory)
            with tarfile.open(archive) as bundle:
                bundle.extractall(root, filter="data")
            provenance = json.loads((root / "PROVENANCE.json").read_text())
            self.assertIn(provenance["platform"], ("linux-x64", "windows-x64", "macos-arm64"))
            recipe = Path(__file__).resolve().parents[2] / "ffmpeg/sources.json"
            expected_version = os.environ.get("NOVELTEA_FFMPEG_VERSION") or json.loads(
                recipe.read_text())["ffmpeg"]["version"]
            self.assertEqual(provenance["components"]["ffmpeg"]["version"], expected_version)
            if "NOVELTEA_FFMPEG_RELEASE_TAG" in os.environ:
                self.assertEqual(provenance["release_tag"], os.environ["NOVELTEA_FFMPEG_RELEASE_TAG"])
            self.assertEqual(len(provenance["recipe_revision"]), 40)
            if provenance["platform"] == "windows-x64":
                self.assertTrue((root / "configuration/toolchain-packages.txt").is_file())
                self.assertTrue(list((root / "licenses/platform-toolchain").rglob("COPYING*")))
            self.assertEqual({path.name for path in (root / "sources").iterdir() if path.is_file()},
                             {info["archive"] for info in provenance["components"].values()})
            for component, info in provenance["components"].items():
                with self.subTest(component=component):
                    self.assertEqual(digest(root / "sources" / info["archive"]), info["sha256"])
                    self.assertTrue(list((root / "licenses" / component).iterdir()))
            for path in ("NOTICE.txt", "BUILD.log", "configuration/ffmpeg-config.h",
                         "configuration/ffmpeg-config.log", "configuration/ffmpeg-buildconf.txt",
                         "sources/build-recipe/ffmpeg/build.sh",
                         "sources/build-recipe/ffmpeg/package.py",
                         "sources/build-recipe/ffmpeg/sources.json",
                         "sources/build-recipe/ffmpeg/README.md"):
                self.assertTrue((root / path).is_file(), path)
            files = set()
            for line in (root / "SHA256SUMS").read_text().splitlines():
                expected, relative = line.split("  ", 1)
                self.assertNotIn(relative, files)
                files.add(relative)
                self.assertEqual(digest(root / relative), expected, relative)
            self.assertEqual(files, {path.relative_to(root).as_posix()
                                     for path in root.rglob("*")
                                     if path.is_file() and path.name != "SHA256SUMS"})
            executables = list((root / "bin").iterdir())
            self.assertEqual(len(executables), 1)
            binary = executables[0]
            self.assertIn(binary.name, ("ffmpeg", "ffmpeg.exe"))
            version = subprocess.check_output([str(binary), "-version"], text=True)
            self.assertIn(f"ffmpeg version {expected_version} ", version)
            environment = dict(os.environ, NOVELTEA_FFMPEG=str(binary))
            subprocess.run([
                sys.executable, "-m", "unittest", "discover", "-s",
                str(root / "sources/build-recipe/tests/ffmpeg"),
                "-p", "test_artifact.py", "-v",
            ], env=environment, check=True, timeout=300)


if __name__ == "__main__":
    unittest.main()
