#!/usr/bin/env python3
"""
Extract all items from an Allwinner "IMAGEWTY" firmware image (.awimg / .img).

Format (v3, header_version == 0x300), reverse-engineered against TrimUI Brick's
trimui_tg3040.awimg and cross-checked against Ithamar/awutils (imagewty.h, awimage.c):

Main header (first 0x400 bytes of the file, item table starts right after):
  0x00  8   magic "IMAGEWTY"
  0x08  4   header_version (0x300)
  0x0C  4   header_size
  0x3C  4   num_files      <- item count

Per-item header, 1024 (0x400) bytes each, item i at file offset 1024*(1+i):
  0x00  4   filename_len
  0x04  4   total_header_size (1024)
  0x08  8   maintype   (e.g. "COMMON", "RFSFAT16", "12345678")
  0x10  16  subtype    (e.g. "BOOT_FEX00000000")
  0x20  4   unknown
  0x24  256 filename, NUL-terminated
  0x124 4   stored_length
  0x128 4   pad
  0x12C 4   original_length
  0x130 4   pad
  0x134 4   offset     <- absolute offset of this item's data in the file

No encryption when the magic is plaintext "IMAGEWTY" (RC6 encryption is only used
when the magic itself is scrambled) — true for every TrimUI Brick release we've seen.
"""
import struct
import sys
import os


def parse_items(data):
    magic = data[0:8]
    if magic != b"IMAGEWTY":
        raise ValueError(f"not an IMAGEWTY image (magic={magic!r})")
    header_version = struct.unpack_from("<I", data, 8)[0]
    if header_version != 0x300:
        raise ValueError(f"unsupported header_version {header_version:#x} (only 0x300 handled)")
    num_files = struct.unpack_from("<I", data, 0x3C)[0]

    items = []
    for i in range(num_files):
        rec_off = 1024 * (1 + i)
        rec = data[rec_off:rec_off + 1024]
        maintype = rec[0x08:0x10].split(b"\x00")[0].decode(errors="replace")
        subtype = rec[0x10:0x20].split(b"\x00")[0].decode(errors="replace")
        filename = rec[0x24:0x24 + 256].split(b"\x00")[0].decode(errors="replace")
        stored_length = struct.unpack_from("<I", rec, 0x124)[0]
        original_length = struct.unpack_from("<I", rec, 0x12C)[0]
        offset = struct.unpack_from("<I", rec, 0x134)[0]
        items.append(dict(
            filename=filename, maintype=maintype, subtype=subtype,
            offset=offset, stored_length=stored_length, original_length=original_length,
        ))
    return items


def main():
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <image.awimg> <output_dir>", file=sys.stderr)
        sys.exit(1)

    image_path, out_dir = sys.argv[1], sys.argv[2]
    with open(image_path, "rb") as f:
        data = f.read()

    items = parse_items(data)
    os.makedirs(out_dir, exist_ok=True)

    for it in items:
        out_path = os.path.join(out_dir, it["filename"])
        length = it["original_length"]
        blob = data[it["offset"]:it["offset"] + length]
        with open(out_path, "wb") as f:
            f.write(blob)
        print(f"{it['filename']:24s} {it['maintype']:10s} {it['subtype']:18s} "
              f"{length:>10d} bytes -> {out_path}")


if __name__ == "__main__":
    main()
