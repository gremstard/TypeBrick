#!/usr/bin/env python3
"""
Split a standard Android boot.img (v0 header) into kernel/ramdisk/second/dtb.

TrimUI Brick's extracted boot.fex is a plain AOSP bootimg:
  magic="ANDROID!", kernel_addr=0x40080000, ramdisk_addr=0x42000000, page_size=2048

Header layout (v0, 2048-byte page-aligned sections after a 1-page header):
  0x00   8   magic "ANDROID!"
  0x08   4   kernel_size
  0x0C   4   kernel_addr
  0x10   4   ramdisk_size
  0x14   4   ramdisk_addr
  0x18   4   second_size
  0x1C   4   second_addr
  0x20   4   tags_addr
  0x24   4   page_size
  0x28   4   header_version
  0x2C   4   os_version
  0x30   16  name
  0x40   512 cmdline
  0x240  32  id
  0x260  1024 extra_cmdline
"""
import struct
import sys
import os


def main():
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <boot.fex> <output_dir>", file=sys.stderr)
        sys.exit(1)

    path, out_dir = sys.argv[1], sys.argv[2]
    with open(path, "rb") as f:
        data = f.read()

    magic = data[0:8]
    if magic != b"ANDROID!":
        raise ValueError(f"not an Android bootimg (magic={magic!r})")

    kernel_size, kernel_addr, ramdisk_size, ramdisk_addr, second_size, second_addr, \
        tags_addr, page_size = struct.unpack_from("<8I", data, 8)
    cmdline = data[0x40:0x40 + 512].split(b"\x00")[0].decode(errors="replace")

    def pages(n):
        return (n + page_size - 1) // page_size

    os.makedirs(out_dir, exist_ok=True)
    off = page_size  # header occupies 1 page

    kernel = data[off:off + kernel_size]
    with open(os.path.join(out_dir, "kernel.Image"), "wb") as f:
        f.write(kernel)
    off += pages(kernel_size) * page_size

    ramdisk = data[off:off + ramdisk_size]
    with open(os.path.join(out_dir, "ramdisk.cpio"), "wb") as f:
        f.write(ramdisk)
    off += pages(ramdisk_size) * page_size

    if second_size:
        second = data[off:off + second_size]
        with open(os.path.join(out_dir, "second.bin"), "wb") as f:
            f.write(second)
        off += pages(second_size) * page_size

    print(f"kernel_addr={kernel_addr:#x} kernel_size={kernel_size} -> kernel.Image")
    print(f"ramdisk_addr={ramdisk_addr:#x} ramdisk_size={ramdisk_size} -> ramdisk.cpio")
    print(f"tags_addr={tags_addr:#x} page_size={page_size} second_size={second_size}")
    print(f"cmdline={cmdline!r}")


if __name__ == "__main__":
    main()
