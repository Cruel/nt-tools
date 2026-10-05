# Windows/macOS FFmpeg build review

Reviewed against run [37354561820](https://github.com/Cruel/nt-tools/actions/runs/37354561820)
(FFmpeg 9.0.1, recipe commit `1d8de12`). These are primary-source findings,
not a claim that the corrected native builds have already passed.

## macOS: wrong libvpx platform target

The pinned libvpx 1.17.0 source distinguishes **unnumbered Darwin (iOS)** from
**numbered Darwin (macOS)**:

- `arm*-darwin-*` adds `-miphoneos-version-min` and selects the iPhoneOS SDK.
- The ARM `darwin` branch uses `xcrun --sdk iphoneos` for its tools.
- Numbered `darwin20` through `darwin25` targets instead select the macOS SDK
  and add the target architecture.

Sources: [libvpx configure.sh, SDK/platform selection](https://github.com/webmproject/libvpx/blob/v1.17.0/build/make/configure.sh#L925-L999),
[ARM Darwin toolchain](https://github.com/webmproject/libvpx/blob/v1.17.0/build/make/configure.sh#L1184-L1242),
and [supported targets](https://github.com/webmproject/libvpx/blob/v1.17.0/README).

The failed recipe explicitly passed `--target=arm64-darwin-gcc`. This built an
ARM64 **iOS** library for a macOS executable. FFmpeg 9.0.1's configure probes
libvpx by linking decoder/encoder entry points and emits the observed
`libvpx enabled but no supported decoders found` when all probes fail.
Source: [FFmpeg libvpx probes](https://github.com/FFmpeg/FFmpeg/blob/n9.0.1/configure).
The failed run did not preserve the linker diagnostics, so the exact linker
message remains unobserved, but the incorrect SDK selection is established.

Correction: derive `arm64-darwin<kernel-major>-gcc` from `uname -r` (Darwin 23 on
macOS 14). A differential invocation of the actual upstream configure script on
Linux confirms that the old target emits iPhone deployment flags and the numbered
target emits `-arch arm64` without iPhone flags. That is a target-selection check,
**not** a substitute for a successful native macOS link/encode test.

[FFmpeg's Darwin documentation](https://ffmpeg.org/platform.html#Darwin) identifies
Xcode as the basic toolchain. NASM is required for x86 assembly, not ARM64.
The recipe retains Xcode/clang and native CMake/Ninja builds for libaom/zlib.

## Windows: supported toolchain, unresolved source response

[FFmpeg's native Windows/MSYS2 instructions](https://ffmpeg.org/platform.html#Native-Windows-compilation-using-MSYS2)
require the MinGW-w64 shell/toolchain, make, pkgconf, diffutils and NASM. The
workflow already uses **MINGW64** with native GCC/CMake/Ninja/NASM/pkgconf;
Python is a scripting utility, not a compiler/runtime dependency of FFmpeg.
The failure occurred **before compilation**, while verifying the zlib download.
There is no evidence that changing GCC, switching to MSVC, or disabling source
verification would address this error.

The pinned [zlib 1.3.2 archive](https://zlib.net/fossils/zlib-1.3.2.tar.gz) still
hashes to `bb329a0a2cd0274d05519d61c667c062e06990d72e125ee2dfa8de64f0119d16`
on this Linux host, and the original macOS job also verified/built zlib. The
Windows job discarded the rejected file and did not report its actual hash,
size or response type. A different/truncated upstream response, an edge/proxy
response, or platform-specific I/O remain distinguishable hypotheses; none is
confirmed from the old log.

Changes:

- Prepare **all four verified source archives** on the Linux preparation runner,
  then distribute the same bytes/manifest to every platform. Native builds still
  verify each archive; no checksum is weakened or replaced to accept bad bytes.
- Quarantine rejected downloads and report expected/actual hashes, byte count,
  and content type (or `cached`), without dumping request/auth headers.
- Preserve build/configure logs and pkg-config records as failure artifacts.
- Install Perl/diffutils explicitly on Windows. The pinned libaom README lists
  Perl as a prerequisite and NASM as an x86 assembler; select NASM explicitly
  rather than accidentally choosing an unrelated host Yasm.

Sources: [libaom build prerequisites](https://aomedia.googlesource.com/aom/+/refs/tags/v3.15.1/README.md),
[MSYS2 pkg-config relocation and static flags](https://www.msys2.org/docs/pkgconfig/),
[MSYS2 filesystem/native path conversion](https://www.msys2.org/docs/filesystem-paths/),
and [zlib's pinned CMake source](https://github.com/madler/zlib/blob/v1.3.2/CMakeLists.txt).
The zlib static target/options and MinGW static archive naming agree with the
existing recipe; no speculative zlib compiler changes are warranted.

## Next native feedback loop

Run **FFmpeg Release** with `ffmpeg_version=9.0.1`, an unused release label, and
`publish_release=false`. This executes source verification, native compilation,
relocation, dependency closure, and AV1/VP9 roundtrips, but cannot create a release.
On failure, download `ffmpeg-diagnostics-<platform>` (or
`ffmpeg-source-diagnostics` for preparation failures). Configure/link errors will
be in `ffbuild/config.log`; download mismatches retain both a JSON report and
`.rejected` bytes. Diagnostic artifacts expire after seven days.
