# nt-tools

## NovelTea FFmpeg (authoring/export only)

Manually run **FFmpeg Release** (`.github/workflows/ffmpeg-release.yml`) with an
upstream version such as `7.1.5` and a new release tag/title such as `ffmpeg-r1`.
It publishes `noveltea-ffmpeg-{linux-x64,windows-x64,macos-arm64}.tar.gz` and adjacent
SHA-256 checksums in that separate release. Each contains the private, relocatable
`ffmpeg` executable, exact corresponding sources, licenses, provenance, and build records.
The LGPL-oriented configuration retains broad local-file import support and
statically linked AV1/VP9 encoders. It is not a game-runtime dependency.
Uncheck `publish_release` for a build-only diagnostic run; failures retain native
configure/build logs. See [the FFmpeg recipe](ffmpeg/README.md) for policy,
rebuilding, and certification.

## Embedded shader/texture compilers

Publishes the pinned Linux x64 static-library closure used by NovelTea's embedded bgfx shader and
texture compilers. Push a tag to create a GitHub release containing
`noveltea-bgfx-shaderc-linux-x64.tar.gz` and its SHA-256 checksum.

The archive contains the `noveltea_bgfx_shaderc_embedded` and
`noveltea_bimg_texturec_embedded` archives, every required bgfx/bx/bimg static dependency, headers,
shader include resources, and a CMake import file. Consumers include
`cmake/noveltea_shaderc_toolchain.cmake` from an extracted archive and link the independent
`noveltea_shaderc::embedded` and `noveltea_texturec::embedded` targets they use.
