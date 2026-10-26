#!/bin/sh
# Usage: v1.0.0.sh <AVM source dir> <AVM build dir>
set -eu
test "$(git -C "$1" rev-parse HEAD)" = 966a7d7cd6fcf60360caf5dc413b2aeeb65e144d
git -C "$1" diff --quiet HEAD
AVM=$(cd "$2" && pwd)
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
OUT=$ROOT/crates/rav2d/tests/data/avmenc
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
nice -n 10 "$AVM/avmdec" --output-bit-depth=8 "$ROOT/crates/rav2d/tests/data/media/avm-v14.1.0-bus.64x64.l5.obu" \
    -o "$TMP/source.y4m" >/dev/null 2>&1
for name in 8bit 10bit lcr ops; do
    bits=8
    opts=
    case $name in
        10bit) bits=10;;
        lcr) opts=--enable-lcr=1;;
        ops) opts=--enable-operating-point-sets=1;;
    esac
    nice -n 10 python3 "$HERE/crop_y4m.py" "$TMP/source.y4m" "$TMP/input.y4m" \
        --size 64x64 --frames 3 --bitdepth "$bits"
    # shellcheck disable=SC2086 # $opts is an encoder option, or empty.
    nice -n 10 "$AVM/avmenc" --good --cpu-used=5 --end-usage=q --qp=150 --limit=3 --obu \
        $opts -o "$OUT/avmenc-v1-$name.obu" "$TMP/input.y4m" >"$TMP/encode.log" 2>&1 \
        || { cat "$TMP/encode.log"; exit 1; }
    nice -n 10 "$AVM/avmdec" --md5 --rawvideo "$OUT/avmenc-v1-$name.obu" 2>/dev/null \
        > "$TMP/hash"
    cut -d' ' -f1 "$TMP/hash" > "$OUT/avmenc-v1-$name.obu.md5"
done
