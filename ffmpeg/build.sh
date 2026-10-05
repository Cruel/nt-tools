#!/usr/bin/env bash
# Run from any directory with a native compiler (MSYS2 MINGW64 on Windows).
set -euxo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${FFMPEG_WORK:-$ROOT/ffmpeg-build}"
mkdir -p "$WORK"
WORK="$(cd "$WORK" && pwd)"
PREFIX="$WORK/prefix"
STAGE="$WORK/stage"
JOBS="${JOBS:-6}"
PYTHON="${PYTHON:-python3}"
export CC="${CC:-cc}" CXX="${CXX:-c++}"
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig"
export PKG_CONFIG_LIBDIR="$PKG_CONFIG_PATH"
export PATH="$PREFIX/bin:$PATH"
"$PYTHON" "$ROOT/ffmpeg/package.py" fetch "$WORK"
read -r FFMPEG_SOURCE AOM_SOURCE VPX_SOURCE ZLIB_SOURCE < <(
  "$PYTHON" -c 'import json,sys; p=json.load(open(sys.argv[1])); print(*(p[k]["directory"] for k in ("ffmpeg", "aom", "vpx", "zlib")))' "$ROOT/ffmpeg/sources.json"
)
# Start fresh: no reuse of configured objects across changes or platforms.
rm -rf "$PREFIX" "$STAGE" "$WORK/aom-build" "$WORK/zlib-build" "$WORK/ffmpeg-build"
mkdir -p "$PREFIX" "$STAGE" "$WORK/ffmpeg-build"
exec > >(tee "$WORK/build.log") 2>&1
uname -a
"$CC" --version
"$CXX" --version
cmake --version
nasm -v
pkg-config --version
case "$(uname -s)" in
  Linux) PLATFORM=linux-x64; VPX_TARGET=x86_64-linux-gcc; EXTRA=() ;;
  Darwin) PLATFORM=macos-arm64; VPX_TARGET=arm64-darwin-gcc
    sw_vers
    xcodebuild -version
    xcrun --show-sdk-version
    EXTRA=(--disable-videotoolbox --disable-audiotoolbox --disable-securetransport) ;;
  MINGW*|MSYS*) PLATFORM=windows-x64; VPX_TARGET=x86_64-win64-gcc
    pacman -Q > "$WORK/toolchain-packages.txt"
    cat "$WORK/toolchain-packages.txt"
    EXTRA=(--target-os=mingw32 --arch=x86_64 --extra-ldflags=-static) ;;
  *) echo 'Unsupported build host' >&2; exit 1 ;;
esac
case "$PLATFORM:$(uname -m)" in
  linux-x64:x86_64|windows-x64:x86_64|macos-arm64:arm64) ;;
  *) echo 'Build must run natively on the release architecture' >&2; exit 1 ;;
esac
cmake -S "$WORK/src/$ZLIB_SOURCE" -B "$WORK/zlib-build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
  -DZLIB_BUILD_SHARED=OFF -DZLIB_BUILD_TESTING=OFF
cmake --build "$WORK/zlib-build" --target zlibstatic -j "$JOBS"
# Install only the static library, headers and pkg-config record.
mkdir -p "$PREFIX/lib/pkgconfig" "$PREFIX/include"
if [[ -f "$WORK/zlib-build/libz.a" ]]; then
  cp "$WORK/zlib-build/libz.a" "$PREFIX/lib/"
else
  # MinGW adds a static suffix; normalize the archive for pkg-config's -lz.
  cp "$WORK/zlib-build/libzs.a" "$PREFIX/lib/libz.a"
fi
cp "$WORK/src/$ZLIB_SOURCE/zlib.h" "$WORK/zlib-build/zconf.h" "$PREFIX/include/"
cp "$WORK/zlib-build/zlib.pc" "$PREFIX/lib/pkgconfig/"
cmake -S "$WORK/src/$AOM_SOURCE" -B "$WORK/aom-build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -DCMAKE_INSTALL_LIBDIR=lib -DBUILD_SHARED_LIBS=OFF \
  -DENABLE_DOCS=OFF -DENABLE_EXAMPLES=OFF -DENABLE_TESTS=OFF \
  -DENABLE_TOOLS=OFF -DCMAKE_POSITION_INDEPENDENT_CODE=ON
cmake --build "$WORK/aom-build" -j "$JOBS"
cmake --install "$WORK/aom-build"
(
  cd "$WORK/src/$VPX_SOURCE"
  ./configure --prefix="$PREFIX" --target="$VPX_TARGET" \
    --disable-shared --enable-static --enable-pic --enable-vp9-highbitdepth --as=nasm \
    --disable-examples --disable-tools --disable-docs --disable-unit-tests
  make -j "$JOBS"
  make install
)
(
  cd "$WORK/ffmpeg-build"
  "$WORK/src/$FFMPEG_SOURCE/configure" --prefix="$PREFIX" \
    --cc="$CC" --cxx="$CXX" --disable-autodetect \
    --disable-gpl --disable-nonfree --disable-version3 \
    --disable-shared --enable-static --pkg-config-flags=--static \
    --extra-cflags="-I$PREFIX/include" --extra-ldflags="-L$PREFIX/lib" \
    --enable-libaom --enable-libvpx --enable-zlib \
    --disable-programs --enable-ffmpeg --disable-doc \
    --disable-network --disable-devices --disable-protocols \
    --enable-protocol=file,pipe --disable-avdevice \
    --disable-hwaccels --disable-vulkan --disable-debug "${EXTRA[@]}"
  make -j "$JOBS"
)
"$PYTHON" "$ROOT/ffmpeg/package.py" stage "$WORK" "$PLATFORM"
