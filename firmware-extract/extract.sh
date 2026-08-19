#!/usr/bin/env bash
# Extracts kernel, DTB, u-boot, boot0, and partition-table info from the stock
# TrimUI Brick firmware zip into firmware-extract/out/.
#
# Requires fetch_stock_firmware.sh to have run first (or a firmware zip already
# present in downloads/). The zip uses LZMA compression which macOS/BSD `unzip`
# can't handle, so we extract via Python's zipfile module instead.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOWNLOADS="$HERE/downloads"
OUT="$HERE/out"
mkdir -p "$OUT"

ZIP="$(cat "$DOWNLOADS/.latest_firmware_zip" 2>/dev/null || true)"
if [[ -z "$ZIP" || ! -f "$ZIP" ]]; then
    echo "No firmware zip found - run fetch_stock_firmware.sh first" >&2
    exit 1
fi

echo "Using firmware zip: $ZIP"

# The zip contains a single .awimg (Allwinner IMAGEWTY container) plus release notes/images.
AWIMG_NAME="$(python3 -c "
import zipfile
z = zipfile.ZipFile('$ZIP')
names = [n for n in z.namelist() if n.endswith('.awimg')]
assert len(names) == 1, names
print(names[0])
")"

WORK="$OUT/_awimg"
mkdir -p "$WORK"
if [[ ! -f "$WORK/$AWIMG_NAME" ]]; then
    python3 -c "
import zipfile
z = zipfile.ZipFile('$ZIP')
z.extract('$AWIMG_NAME', '$WORK')
"
fi

echo "Parsing IMAGEWTY container: $AWIMG_NAME"
python3 "$HERE/extract_imagewty.py" "$WORK/$AWIMG_NAME" "$OUT"

echo "Splitting boot.fex (Android bootimg) into kernel/ramdisk"
python3 "$HERE/parse_bootimg.py" "$OUT/boot.fex" "$OUT/boot_split"

echo
echo "=== Key artifacts ==="
echo "Kernel Image:     out/boot_split/kernel.Image"
echo "DTB blob(s):       out/sunxi.fex (device-tree config package, needs further split)"
echo "u-boot:             out/u-boot.fex"
echo "boot0 (SPL):        out/boot0_sdcard.fex"
echo "Partition layout:   out/sys_partition.fex (text, sector sizes)"
echo "Root filesystem:    out/rootfs.fex (ext4, 566MB - kernel modules live here,"
echo "                    needs a Linux host with ext4 tools/loop-mount to read)"
echo
echo "NOTE: rootfs.fex is ext4 and cannot be mounted read on macOS without extra"
echo "tooling. Kernel module extraction (wifi/bt/gpu) happens on the Linux build host."
