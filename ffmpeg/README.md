# NovelTea FFmpeg release recipe

FFmpeg is a **separate-process authoring/export tool**, never a game-runtime
library. Consumers download a release archive, verify its adjacent `.sha256`,
and stage `bin/ffmpeg` (or `bin/ffmpeg.exe`) in a private installation-relative
tools directory, **not** the PATH-exposed NovelTea CLI directory.

## Manual releases

In GitHub Actions, choose **FFmpeg Release** → **Run workflow**, select the recipe
branch, and enter:

- `ffmpeg_version`: upstream release number, e.g. `7.1.5`. Branch names, `n7.1.5`
  Git tags and URLs are not accepted. The release must work with this recipe.
- `release_tag`: a new GitHub release tag **and title**, e.g. `r1` or `ffmpeg-r1`.
  This is independent of the upstream FFmpeg version.
- `publish_release`: defaults to true. Uncheck it for a build-only diagnostic run;
  artifacts/certification still run, but no release/tag is created. Use an unused label.

Or use:

```sh
gh workflow run ffmpeg-release.yml -f ffmpeg_version=7.1.5 -f release_tag=ffmpeg-r1
```

The workflow rejects invalid/existing tags or releases, builds and certifies Linux
x64, Windows x64 and macOS arm64, then creates a separate release at the selected
recipe commit. All three builds must pass before publication. Reusing a label does
not overwrite a release; choose a new one to retry after publishing. Archive names
remain `noveltea-ffmpeg-<platform>.tar.gz` regardless of the label. Tag pushes to
`.github/workflows/release.yml` still publish only the shader/texture tools.

## Source selection and policy

`sources.json` supplies the local/default pins: FFmpeg 7.1.5 (maintained 7.1 branch),
libaom 3.15.1, libvpx 1.17.0, and zlib 1.3.2. External-library versions stay pinned
when selecting another FFmpeg release. No source patches are applied.

The manual workflow downloads `https://ffmpeg.org/releases/ffmpeg-<version>.tar.xz`
once over HTTPS, computes its SHA-256, and distributes that archive and a generated
manifest to every platform. The default version is also checked against the
repository's known checksum. Other versions trust the upstream HTTPS download at
selection time; their checksum is frozen for that run, not independently
pre-approved in this repository. The preparation job also downloads and verifies all external-library source
archives, and distributes that identical complete closure to each runner. Each
native build then verifies every archive against the selected manifest. The generated manifest and exact source bytes ship
in every release, alongside the requested release label and recipe commit.

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

To build, certify and package the local pins, run `bash ffmpeg/certify.sh`.
To reproduce manual selection locally:

```sh
python3 ffmpeg/package.py select /tmp/ffmpeg-selected-source 7.1.5
NOVELTEA_FFMPEG_VERSION=7.1.5 NOVELTEA_FFMPEG_RELEASE_TAG=ffmpeg-r1 \
  bash ffmpeg/certify.sh /tmp/ffmpeg-selected-source
```

Passing a selected source bundle updates the checkout's `ffmpeg/sources.json` to
that manifest. Or run the individual local-pin steps:

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
Sources are cached only as checksum-verified archives. Failed verification remains
fatal, but retains the bad bytes as `<archive>.rejected` and a
`<archive>.download.json` report with actual/expected hashes, byte count and
response content type. These diagnostic files are excluded from release packages.

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
then validates the packaged source, requested version/label, and checksums.
The source/build identity is pinned per release; bit-for-bit reproducibility
across changing host compiler/SDK versions is not claimed.

On failure, the manual workflow retains `ffmpeg-diagnostics-<platform>` artifacts
with build/configure logs, toolchain records and pkg-config files for seven days.
Preparation download failures retain `ffmpeg-source-diagnostics`. See
[the Windows/macOS review](PLATFORM-NOTES.md) for the upstream platform guidance,
macOS libvpx target correction, and remaining Windows diagnosis.
