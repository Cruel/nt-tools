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
                                     "libdl.so.2", "librt.so.1", "libgcc_s.so.1", "libstdc++.so.6", "ld-linux-x86-64.so.2"})

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

    def test_static_zimg_filter_and_execution(self):
        configuration = self.ffmpeg("-buildconf").stdout
        self.assertIn("--enable-libzimg", configuration)
        filters = self.ffmpeg("-filters").stdout
        self.assertIn("zscale", filters)
        self.assertIn("tonemap", filters)
        with tempfile.TemporaryDirectory(prefix="noveltea zscale ") as directory:
            source = Path(directory) / "rgb.input"
            source.write_bytes(bytes((64,)) * (32 * 32) + bytes((128,)) * (32 * 32 // 2))
            result = subprocess.run([
                self.binary, "-hide_banner", "-nostdin", "-v", "error",
                "-f", "rawvideo", "-pixel_format", "yuv420p",
                "-video_size", "32x32", "-framerate", "1",
                "-i", str(source), "-vf", "zscale=w=16:h=16,format=yuv420p",
                "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "yuv420p", "pipe:1",
            ], capture_output=True, check=True, timeout=120)
            self.assertEqual(len(result.stdout), 16 * 16 * 3 // 2)

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

    def test_webp_still_and_animated_encoding(self):
        import shutil
        configuration = self.ffmpeg("-buildconf").stdout
        self.assertIn("--enable-libwebp", configuration)
        encoders = self.ffmpeg("-encoders").stdout
        self.assertIn("libwebp", encoders)
        self.assertIn("libwebp_anim", encoders)
        with tempfile.TemporaryDirectory(prefix="noveltea webp ") as directory:
            root = Path(directory)
            binary = root / Path(self.binary).name
            shutil.copy2(self.binary, binary)
            frames = (bytes([200, 30, 30]) * (64 * 64)
                      + bytes([30, 200, 30]) * (64 * 64)
                      + bytes([30, 30, 200]) * (64 * 64))
            source = root / "input.rgb"
            source.write_bytes(frames)
            animated = root / "anim.webp"
            subprocess.run([
                str(binary), "-nostdin", "-v", "error", "-y",
                "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", "64x64",
                "-framerate", "3", "-i", str(source), "-an", "-c:v", "libwebp_anim",
                "-pix_fmt", "yuv420p", str(animated),
            ], check=True, timeout=120)
            self.assertTrue(animated.is_file())
            self.assertGreater(animated.stat().st_size, 0)
            decoded = subprocess.run([
                str(binary), "-nostdin", "-v", "error", "-i", str(animated),
                "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
            ], check=True, capture_output=True, timeout=120).stdout
            self.assertEqual(len(decoded), len(frames))
            self.assertLess(max(abs(a - b) for a, b in zip(decoded, frames)), 25)
            still_source = root / "still.rgb"
            still_source.write_bytes(bytes([64, 128, 192]) * (64 * 64))
            still = root / "still.webp"
            subprocess.run([
                str(binary), "-nostdin", "-v", "error", "-y",
                "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", "64x64",
                "-framerate", "1", "-i", str(still_source),
                "-frames:v", "1", "-c:v", "libwebp", "-pix_fmt", "yuv420p",
                str(still),
            ], check=True, timeout=120)
            still_decoded = subprocess.run([
                str(binary), "-nostdin", "-v", "error", "-i", str(still),
                "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
            ], check=True, capture_output=True, timeout=120).stdout
            self.assertEqual(len(still_decoded), 64 * 64 * 3)

    def test_webp_variable_timing_and_exact_alpha(self):
        # VFR input and the final hold must remain exact in the animated WebP.
        # Inspect the RIFF ANMF durations: FFmpeg's decoded frame count does not
        # expose WebP animation frame holds.
        with tempfile.TemporaryDirectory(prefix="noveltea alpha vfr ") as directory:
            root = Path(directory)
            width = height = 16
            masks = (
                bytes((0, 1, 127, 128, 254, 255)[(x + 3*y) % 6]
                      for y in range(height) for x in range(width)),
                bytes(128 if 4 <= x < 12 and 4 <= y < 12 else 0
                      for y in range(height) for x in range(width)),
                bytes(255 if x >= 8 and y >= 8 else 0
                      for y in range(height) for x in range(width)),
            )
            paths = []
            for index, mask in enumerate(masks):
                rgba = b"".join(bytes((255, 255, 255, alpha)) for alpha in mask)
                path = root / f"alpha-{index}.png"
                subprocess.run([
                    self.binary, "-nostdin", "-v", "error", "-y",
                    "-f", "rawvideo", "-pixel_format", "bgra",
                    "-video_size", f"{width}x{height}", "-i", "pipe:0",
                    "-frames:v", "1", str(path),
                ], input=rgba, check=True, capture_output=True, timeout=120)
                paths.append(path)

            manifest = root / "timeline.ffconcat"
            # All boundaries are multiples of 50 ms, so a 20 fps image
            # timebase also conveys the last PNG packet's 50 ms duration.
            manifest.write_text("\n".join(
                ["ffconcat version 1.0"] +
                [line for path, milliseconds in zip(paths, (200, 550, 50))
                 for line in (f"file '{path}'", "option framerate 20",
                              f"duration {milliseconds / 1000:.3f}")]
            ) + "\n")
            animated = root / "alpha.webp"
            subprocess.run([
                self.binary, "-nostdin", "-v", "error", "-y",
                "-safe", "0", "-f", "concat", "-i", str(manifest),
                "-fps_mode", "passthrough", "-c:v", "libwebp_anim",
                "-lossless", "1", "-pix_fmt", "bgra", str(animated),
            ], check=True, capture_output=True, timeout=120)

            blob = animated.read_bytes()
            self.assertEqual(blob[:4], b"RIFF")
            self.assertEqual(blob[8:12], b"WEBP")
            durations = []
            at = 12
            while at < len(blob):
                tag = blob[at:at + 4]
                size = int.from_bytes(blob[at + 4:at + 8], "little")
                if tag == b"ANMF":
                    payload = blob[at + 8:at + 8 + size]
                    durations.append(int.from_bytes(payload[12:15], "little"))
                    self.assertIn(b"VP8L", payload)
                at += 8 + size + (size & 1)
            self.assertEqual(at, len(blob))
            self.assertEqual(durations, [200, 550, 50])
            decoded = subprocess.run([
                self.binary, "-nostdin", "-v", "error", "-i", str(animated),
                "-fps_mode", "passthrough", "-f", "rawvideo",
                "-pix_fmt", "bgra", "pipe:1",
            ], check=True, capture_output=True, timeout=120).stdout
            self.assertEqual(len(decoded), len(masks) * width * height * 4)
            for index, expected in enumerate(masks):
                start = index * width * height * 4
                actual = decoded[start:start + width * height * 4]
                self.assertEqual(actual[3::4], expected)


if __name__ == "__main__":
    unittest.main()
