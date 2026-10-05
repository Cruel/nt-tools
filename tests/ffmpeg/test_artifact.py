"""Certification at the released executable boundary (no system FFmpeg fallback)."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class ExecutableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary = str(Path(os.environ["NOVELTEA_FFMPEG"]).resolve())

    def ffmpeg(self, *args):
        return subprocess.run(
            [self.binary, "-hide_banner", "-nostdin", *args],
            check=True, capture_output=True, text=True, timeout=120,
        )

    def test_lgpl_local_file_tool(self):
        license_text = " ".join(self.ffmpeg("-L").stdout.split())
        self.assertIn("GNU Lesser General Public License", license_text)
        self.assertNotIn("GNU General Public License", license_text)
        self.assertIn("version 2.1", license_text)
        protocols = self.ffmpeg("-protocols").stdout.split("Input:", 1)[1]
        self.assertEqual(set(protocols.replace("Output:", "").split()), {"file", "pipe"})
        devices = self.ffmpeg("-devices").stdout.splitlines()
        self.assertFalse(any(line.startswith((" D ", "  E", " DE")) for line in devices))

    def test_only_platform_runtime_dependencies(self):
        import re
        import sys
        if self.binary.endswith(".exe"):
            output = subprocess.check_output(["objdump", "-p", self.binary], text=True)
            dependencies = re.findall(r"DLL Name:\s*(\S+)", output)
            allowed = {"kernel32.dll", "msvcrt.dll", "ucrtbase.dll", "advapi32.dll",
                       "user32.dll", "shell32.dll", "ole32.dll", "bcrypt.dll",
                       "ws2_32.dll", "secur32.dll", "psapi.dll"}
            self.assertTrue(dependencies)
            for name in dependencies:
                self.assertTrue(name.lower() in allowed or
                                name.lower().startswith(("api-ms-win-", "ext-ms-win-")), name)
        elif sys.platform == "darwin":
            output = subprocess.check_output(["otool", "-L", self.binary], text=True)
            dependencies = [line.strip().split()[0] for line in output.splitlines()[1:]]
            self.assertTrue(dependencies)
            for name in dependencies:
                self.assertTrue(name.startswith(("/usr/lib/", "/System/Library/")), name)
        else:
            output = subprocess.check_output(["readelf", "-d", self.binary], text=True)
            dependencies = re.findall(r"\(NEEDED\).*\[(.*?)\]", output)
            self.assertTrue(dependencies)
            for name in dependencies:
                self.assertIn(name, {"libc.so.6", "libm.so.6", "libpthread.so.0",
                                     "libdl.so.2", "librt.so.1", "libgcc_s.so.1"})

    def test_broad_import_support(self):
        decoders = self.ffmpeg("-decoders").stdout.split()
        for codec in ("h264", "hevc", "vp8", "vp9", "av1", "prores", "dnxhd",
                      "mjpeg", "png", "tiff", "gif", "ffv1", "aac", "mp3", "flac"):
            with self.subTest(codec=codec):
                self.assertIn(codec, decoders)
        formats = self.ffmpeg("-demuxers").stdout
        for container in ("mov,mp4", "matroska,webm", "avi", "mpegts", "image2", "wav", "ogg"):
            with self.subTest(container=container):
                self.assertIn(container, formats)

    def test_relocated_av1_vp9_roundtrip(self):
        import shutil
        with tempfile.TemporaryDirectory(prefix="noveltea media ") as directory:
            root = Path(directory)
            binary = root / Path(self.binary).name
            shutil.copy2(self.binary, binary)
            frame = bytes([64, 128, 192]) * (64 * 64)
            source = root / "input.rgb"
            source.write_bytes(frame * 3)
            for codec in ("libaom-av1", "libvpx-vp9"):
                with self.subTest(codec=codec):
                    encoded = root / (codec + ".webm")
                    subprocess.run([
                        str(binary), "-nostdin", "-v", "error", "-y",
                        "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", "64x64",
                        "-framerate", "3", "-i", str(source), "-an", "-c:v", codec,
                        "-threads", "2", "-cpu-used", "8", "-pix_fmt", "yuv420p",
                        str(encoded),
                    ], check=True, timeout=120)
                    decoded = subprocess.run([
                        str(binary), "-nostdin", "-v", "error", "-i", str(encoded),
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
                    ], check=True, capture_output=True, timeout=120).stdout
                    self.assertEqual(len(decoded), len(frame) * 3)
                    self.assertLess(max(abs(a - b) for a, b in zip(decoded, frame * 3)), 12)


if __name__ == "__main__":
    unittest.main()
