# NovelTea FFmpeg release recipe

FFmpeg is a **separate-process authoring/export tool**, never a game-runtime
library. Consumers download a release archive, verify its adjacent `.sha256`,
and stage `bin/ffmpeg` (or `bin/ffmpeg.exe`) in a private installation-relative
tools directory, **not** the PATH-exposed NovelTea CLI directory.

## Pins and policy

`sources.json` pins release revisions and exact source-archive SHA-256 values:
FFmpeg 7.1.5 (maintained 7.1 branch), libaom 3.15.1, libvpx 1.17.0, and zlib 1.3.2. Downloads fail closed
on checksum mismatch. No patches are applied. Update pins and run all three
platform certifications before tagging a new tool release.

FFmpeg is LGPL-2.1-or-later in this configuration: GPL, nonfree and version3
features are explicitly disabled. libaom (AV1) and libvpx (VP9) provide the admitted
output encoders, with static zlib for compressed image/media imports. All internal
local-file demuxers/decoders and software filters remain enabled by default.
External autodetection is disabled so host packages cannot silently change the
closure/license. Network, capture/device, hardware accelerators, ffplay and ffprobe
are excluded. Only `file` and `pipe` protocols are admitted. Native OS runtime
libraries/frameworks are allowed; external codec/compression libraries are static.
Codec patent rights require separate review; this software-license configuration
makes no patent-clearance claim.

## Rebuild / modify / relink

Use Python >=3.12, Bash, C/C++, make, CMake, Ninja, NASM, and pkg-config. Native
release hosts are Ubuntu 22.04 x64, macOS 14 arm64 with Xcode command-line tools
and Homebrew build tools, or Windows 2022 x64 with MSYS2 MINGW64. Windows uses
`CC=gcc CXX=g++` and the MSYS Python interpreter. The release workflow records
these installations; `BUILD.log` records compiler versions and executed commands.
macOS OS/Xcode/SDK versions are also recorded. Windows packages are identified in
`configuration/toolchain-packages.txt`; MinGW runtime/toolchain notices and the
GCC Runtime Library Exception are retained under `licenses/platform-toolchain/`.
Normal system SDK/runtime dependencies are not redistributed.

To build, certify and package in one step, run `bash ffmpeg/certify.sh`.
Or run the individual steps:

```sh
bash ffmpeg/build.sh
NOVELTEA_FFMPEG="$PWD/ffmpeg-build/stage/bin/ffmpeg" \
  python3 -m unittest discover -s tests/ffmpeg -p test_artifact.py -v
python3 ffmpeg/package.py archive ffmpeg-build linux-x64
NOVELTEA_FFMPEG_ARCHIVE="$PWD/ffmpeg-build/noveltea-ffmpeg-linux-x64.tar.gz" \
  python3 -m unittest discover -s tests/ffmpeg -p test_package.py -v
```

Use `.exe` and the appropriate platform name on Windows. Use `macos-arm64` on Mac.
`FFMPEG_WORK` selects a disposable work directory; `JOBS` defaults to 6.
The build removes old extracted sources and build outputs before rebuilding.
Sources are cached only as checksum-verified archives.

Each release includes **complete corresponding source archives**, the recipe and
certification scripts under `sources/build-recipe/`, original license/patent
notices, FFmpeg configuration/logs, external-library configuration, compiler/build
records, `PROVENANCE.json`, `NOTICE.txt`, and file checksums. No source offer or
upstream download availability is needed to obtain the corresponding source.
For an offline rebuild, copy the bundled source archives into
`ffmpeg-build/sources/` under the extracted `sources/build-recipe/` directory,
then run the recipe there. To build modified source, replace its cached archive
and update its checksum in `sources.json`, or edit extracted sources and repeat
the commands in `BUILD.log` (without rerunning the fetch step). This rebuilds and
relinks the entire standalone executable; no proprietary application objects are
needed. Subcomponent copyright/licenses remain available in the full sources.

The archive is relocatable, including paths containing spaces. Certification
encodes and decodes AV1/VP9 WebM from deterministic local raw media, checks useful
import formats/codecs, license/protocol restrictions and native dependency closure,
then validates the packaged source and checksums. Only all-successful platform
builds are published together with the existing shader-tool artifacts on tag push.
The source/build identity is pinned; bit-for-bit reproducibility across changing
host compiler/SDK versions is not claimed.
