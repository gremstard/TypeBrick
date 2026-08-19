#!/usr/bin/env python3
"""
Reassemble a bootable raw SD card image from the stock-firmware items extracted
by extract.sh, using the EXACT offsets from the stock PhoenixCard burn script
(cardscript.fex, found inside the firmware itself):

  sector 16      boot0_sdcard.fex   (SPL, BROM reads this first)
  sector 32800   boot_package.fex   (TOC0: ATF + U-Boot, sun50iw10 boot scheme)
  sector 40960   "card_boot" start  -> sunxi_gpt.fex (protective MBR + GPT header
                                       + partition entries), followed by each
                                       partition's content at
                                       40960 + <partition's first_lba from GPT>

This is a pure repack of the STOCK firmware's own components (unmodified) - a
sanity check that our extraction + offset understanding is correct, before we
build any custom rootfs. It should boot identically to stock TrimUI firmware.

Partition -> source file mapping (from sys_partition.fex / the GPT we parsed):
  bootloader -> boot-resource.fex
  env         -> env.fex
  env-redund  -> env.fex
  boot        -> boot.fex   (contains the kernel we validated)
  rootfs      -> rootfs.fex (566MB, stock ext4 rootfs)
  recovery    -> recovery.fex
  rootfs_data, private, pstore, UDISK -> left zeroed (created fresh on first boot)
"""
import os
import struct
import sys

SECTOR = 512
BOOT0_SECTOR = 16
BOOTPKG_SECTOR = 32800
CARD_BOOT_SECTOR = 40960

PARTITION_FILES = {
    "bootloader": "boot-resource.fex",
    "env": "env.fex",
    "env-redund": "env.fex",
    "boot": "boot.fex",
    "rootfs": "rootfs.fex",
    "recovery": "recovery.fex",
}


def parse_gpt(gpt_bytes):
    hdr = gpt_bytes[512:512 + 92]
    assert hdr[0:8] == b"EFI PART", "not a valid GPT"
    part_entry_lba, = struct.unpack_from("<Q", hdr, 72)
    num_entries, = struct.unpack_from("<I", hdr, 80)
    entry_size, = struct.unpack_from("<I", hdr, 84)

    parts = {}
    entries_off = part_entry_lba * SECTOR
    for i in range(num_entries):
        off = entries_off + i * entry_size
        entry = gpt_bytes[off:off + entry_size]
        if entry[0:16] == b"\x00" * 16:
            continue
        first_lba, last_lba = struct.unpack_from("<QQ", entry, 32)
        name = entry[56:56 + 72].decode("utf-16-le").split("\x00")[0]
        parts[name] = (first_lba, last_lba)
    return parts


def main():
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <extracted_out_dir> <output.img>", file=sys.stderr)
        sys.exit(1)

    out_dir, img_path = sys.argv[1], sys.argv[2]

    def load(name):
        with open(os.path.join(out_dir, name), "rb") as f:
            return f.read()

    gpt_bytes = load("sunxi_gpt.fex")
    parts = parse_gpt(gpt_bytes)
    print("Parsed partitions (relative to card_boot sector):")
    for name, (first, last) in parts.items():
        print(f"  {name:16s} first_lba={first:10d} last_lba={last:10d}")

    max_abs_sector = CARD_BOOT_SECTOR + max(last for _, last in parts.values())
    img_size = (max_abs_sector + 1) * SECTOR

    print(f"\nAllocating image: {img_size / (1024**3):.2f} GiB ({img_size} bytes)")
    with open(img_path, "wb") as img:
        img.truncate(img_size)

        def write_at(sector, data):
            img.seek(sector * SECTOR)
            img.write(data)

        boot0 = load("boot0_sdcard.fex")
        write_at(BOOT0_SECTOR, boot0)
        print(f"boot0_sdcard.fex   -> sector {BOOT0_SECTOR:10d} ({len(boot0)} bytes)")

        bootpkg = load("boot_package.fex")
        write_at(BOOTPKG_SECTOR, bootpkg)
        print(f"boot_package.fex   -> sector {BOOTPKG_SECTOR:10d} ({len(bootpkg)} bytes)")

        write_at(CARD_BOOT_SECTOR, gpt_bytes)
        print(f"sunxi_gpt.fex      -> sector {CARD_BOOT_SECTOR:10d} ({len(gpt_bytes)} bytes)")

        for part_name, filename in PARTITION_FILES.items():
            if part_name not in parts:
                print(f"WARNING: partition {part_name} not found in GPT, skipping")
                continue
            first_lba, _ = parts[part_name]
            abs_sector = CARD_BOOT_SECTOR + first_lba
            data = load(filename)
            write_at(abs_sector, data)
            print(f"{filename:18s} -> sector {abs_sector:10d} ({len(data)} bytes) [{part_name}]")

    print(f"\nDone: {img_path}")


if __name__ == "__main__":
    main()
