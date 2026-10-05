#!/usr/bin/env bash
# Common native release certification, including the extracted download archive.
set -euxo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${FFMPEG_WORK:-$ROOT/ffmpeg-build}"
PYTHON="${PYTHON:-python3}"
bash "$ROOT/ffmpeg/build.sh"
WORK="$(cd "$WORK" && pwd)"
PLATFORM="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["platform"])' "$WORK/stage/PROVENANCE.json")"
SUFFIX=''
if [[ "$PLATFORM" == windows-x64 ]]; then SUFFIX='.exe'; fi
NOVELTEA_FFMPEG="$WORK/stage/bin/ffmpeg$SUFFIX" \
  "$PYTHON" -m unittest discover -s "$ROOT/tests/ffmpeg" -p test_artifact.py -v
"$PYTHON" "$ROOT/ffmpeg/package.py" archive "$WORK" "$PLATFORM"
NOVELTEA_FFMPEG_ARCHIVE="$WORK/noveltea-ffmpeg-$PLATFORM.tar.gz" \
  "$PYTHON" -m unittest discover -s "$ROOT/tests/ffmpeg" -p test_package.py -v
