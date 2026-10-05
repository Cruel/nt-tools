"""Failed source verification remains fail-closed and diagnosable."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class DownloadDiagnosticsTests(unittest.TestCase):
    def test_rejected_cached_download_retains_bytes_and_actual_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recipe = root / "ffmpeg"
            recipe.mkdir()
            shutil.copy2(ROOT / "ffmpeg/package.py", recipe / "package.py")
            component = json.loads((ROOT / "ffmpeg/sources.json").read_text())["zlib"]
            (recipe / "sources.json").write_text(json.dumps({"zlib": component}))
            sources = root / "work/sources"
            sources.mkdir(parents=True)
            payload = b"unexpected upstream response"
            (sources / "zlib.tar.gz").write_bytes(payload)
            result = subprocess.run([
                sys.executable, str(recipe / "package.py"), "fetch", str(root / "work"),
            ], check=False, capture_output=True, text=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            actual = hashlib.sha256(payload).hexdigest()
            self.assertIn("Source checksum mismatch", result.stderr)
            self.assertIn(actual, result.stderr)
            self.assertFalse((sources / "zlib.tar.gz").exists())
            self.assertEqual((sources / "zlib.tar.gz.rejected").read_bytes(), payload)
            report = json.loads((sources / "zlib.tar.gz.download.json").read_text())
            self.assertEqual(report["actual_sha256"], actual)
            self.assertEqual(report["expected_sha256"], component["sha256"])
            self.assertEqual(report["size_bytes"], len(payload))


if __name__ == "__main__":
    unittest.main()
