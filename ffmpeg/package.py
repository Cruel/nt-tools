"""Verified source acquisition and self-contained release packaging."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = json.loads((ROOT / "ffmpeg/sources.json").read_text())


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fetch(work):
    archives = work / "sources"
    archives.mkdir(parents=True, exist_ok=True)
    source = work / "src"
    if source.exists():
        shutil.rmtree(source)
    source.mkdir()
    for component in SOURCES.values():
        archive = archives / component["archive"]
        if not archive.exists():
            with (urllib.request.urlopen(component["url"], timeout=120) as response,
                  archive.open("wb") as output):
                shutil.copyfileobj(response, output)
        if digest(archive) != component["sha256"]:
            archive.unlink()
            raise ValueError(f"Source checksum mismatch: {component['url']}")
        with tarfile.open(archive) as bundle:
            bundle.extractall(source, filter="data")


def stage(work, platform):
    output = work / "stage"
    (output / "bin").mkdir(parents=True, exist_ok=True)
    suffix = ".exe" if platform == "windows-x64" else ""
    binary = output / "bin" / ("ffmpeg" + suffix)
    shutil.copy2(work / "ffmpeg-build" / binary.name, binary)
    shutil.copytree(work / "sources", output / "sources")
    shutil.copytree(ROOT / "ffmpeg", output / "sources/build-recipe/ffmpeg",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "tests/ffmpeg", output / "sources/build-recipe/tests/ffmpeg",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(work / "build.log", output / "BUILD.log")
    configs = output / "configuration"
    configs.mkdir()
    for src, dest in (
        ("ffmpeg-build/config.h", "ffmpeg-config.h"),
        ("ffmpeg-build/ffbuild/config.mak", "ffmpeg-config.mak"),
        ("ffmpeg-build/ffbuild/config.log", "ffmpeg-config.log"),
        ("aom-build/CMakeCache.txt", "aom-CMakeCache.txt"),
        ("zlib-build/CMakeCache.txt", "zlib-CMakeCache.txt"),
        (f"src/{SOURCES['vpx']['directory']}/config.log", "vpx-config.log"),
        (f"src/{SOURCES['vpx']['directory']}/vpx_config.h", "vpx-config.h"),
    ):
        shutil.copy2(work / src, configs / dest)
    licenses = output / "licenses"
    licenses.mkdir()
    if platform == "windows-x64":
        # Static MinGW compiler/CRT/pthread runtimes retain their notices and GCC
        # Runtime Library Exception, independently of FFmpeg's LGPL policy.
        shutil.copytree(Path(os.environ["MINGW_PREFIX"]) / "share/licenses",
                        licenses / "platform-toolchain")
        shutil.copy2(work / "toolchain-packages.txt", configs / "toolchain-packages.txt")
    for component, info in SOURCES.items():
        destination = licenses / component
        destination.mkdir()
        for path in (work / "src" / info["directory"]).iterdir():
            if path.is_file() and (path.name.startswith(("LICENSE", "COPYING", "PATENTS"))
                                   or path.name in ("AUTHORS", "CREDITS", "README")):
                shutil.copy2(path, destination / path.name)
    buildconf = subprocess.check_output([str(binary), "-buildconf"], stderr=subprocess.STDOUT)
    (configs / "ffmpeg-buildconf.txt").write_bytes(buildconf)
    revision_file = ROOT / "ffmpeg/RECIPE_REVISION"
    revision = os.environ.get("GITHUB_SHA")
    if not revision:
        revision = revision_file.read_text().strip() if revision_file.exists() else subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    (output / "sources/build-recipe/ffmpeg/RECIPE_REVISION").write_text(revision + "\n")
    provenance = {
        "package": "noveltea-ffmpeg-" + platform,
        "platform": platform,
        "release_tag": os.environ.get("GITHUB_REF_NAME", "local"),
        "recipe_revision": revision,
        "components": SOURCES,
        "license": "LGPL-2.1-or-later (FFmpeg); BSD-2-Clause + patent grant (libaom); BSD-3-Clause + patent grant (libvpx); Zlib (zlib)",
        "build_record": "BUILD.log and configuration/",
    }
    (output / "PROVENANCE.json").write_text(json.dumps(provenance, indent=2) + "\n")
    (output / "NOTICE.txt").write_text(
        "NovelTea FFmpeg: private authoring/export tool, not a game-runtime dependency.\n"
        "FFmpeg https://ffmpeg.org/ is LGPL-2.1-or-later in this configuration.\n"
        "No FFmpeg GPL, nonfree or version3 components are enabled. No ffplay/ffprobe.\n"
        "See licenses/ and exact corresponding source archives in sources/.\n"
        "All source and recipes needed to rebuild/relink this executable are included.\n"
        "Run bash sources/build-recipe/ffmpeg/build.sh with the platform toolchain\n"
        "documented in sources/build-recipe/ffmpeg/README.md. To modify a component,\n"
        "replace its archive and checksum in sources.json, or edit extracted sources\n"
        "and rerun the build commands recorded in BUILD.log. No source patches applied.\n"
        "You may replace this separate-process executable with a modified build;\n"
        "NovelTea does not link against libav*. Preserve notices when redistributing.\n"
        "Software licenses do not settle codec patent rights in your jurisdiction.\n"
    )


def archive(work, platform):
    output = work / "stage"
    checksums = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            checksums.append(f"{digest(path)}  {path.relative_to(output).as_posix()}\n")
    (output / "SHA256SUMS").write_text("".join(checksums))
    name = "noveltea-ffmpeg-" + platform + ".tar.gz"
    with tarfile.open(work / name, "w:gz") as bundle:
        for path in sorted(output.iterdir()):
            bundle.add(path, arcname=path.name)
    (work / (name + ".sha256")).write_text(f"{digest(work / name)}  {name}\n")


if __name__ == "__main__":
    command, directory, *args = sys.argv[1:]
    {"fetch": fetch, "stage": stage, "archive": archive}[command](Path(directory).resolve(), *args)
