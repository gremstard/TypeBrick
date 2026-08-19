# Hardware & Firmware Research

Findings from initial research into the TrimUI Brick platform, gathered before starting the
Milestone 1 build. Kept here so we don't have to re-derive this later.

## Device

- SoC: Allwinner **A133p** (rebin of A100), quad-core Cortex-A53
- RAM: 1GB
- Display: 3.2" IPS, ~640x480 (4:3)
- GPU: **Imagination PowerVR GE8300** (Series8XE "Clark", Rogue architecture) — not Mali
- WiFi/Bluetooth: **XR829** combo chip (802.11b/g/n + BT4.2)
- Ports: two USB-C — bottom (charge + OTG data, capped 500mA), top (USB host, for
  controllers/keyboards); headphone jack; microSD boot
- Audio: stereo speakers

## Kernel / bootloader source availability

TrimUI does **not** publish kernel or u-boot source. The [github.com/trimui](https://github.com/trimui)
org only ships binary firmware releases:
- [`trimui/firmware_brick`](https://github.com/trimui/firmware_brick) — TG3040 Brick firmware
- [`trimui/assets_brick`](https://github.com/trimui/assets_brick) — SD card base package
- Sibling repos exist for SmartPro/Smart/BrickPro
- `toolchain_sdk_smartpro` / `_smartpro_s` — userspace app SDKs only, not BSP/kernel

Underlying OS is Allwinner's **Tina Linux** (their internal OpenWrt-derived BSP distro) — a
downstream vendor fork, not mainline-adjacent.

## Community firmware precedent

- [shauninman/MinUI](https://github.com/shauninman/MinUI) — supports Brick and Smart Pro
  directly. Layers a launcher on the **stock vendor kernel/rootfs**; doesn't ship its own
  kernel, repackages the extracted Tina Linux kernel + Allwinner BSP blobs from stock firmware.
- [LoveRetro/NextUI](https://github.com/LoveRetro/NextUI) — MinUI fork/successor, same approach.
- [Knulli](https://knulli.org/devices/trimui/brick/) — explicitly documents using "u-boot and
  kernel extracted from the stock firmware" since TrimUI won't release source. Runs the
  proprietary `pvrsrvkm` GPU driver, extracted and packaged at
  [knulli-cfw/ge8300-drivers](https://github.com/knulli-cfw/ge8300-drivers).

**We're following the same pattern**: extract kernel/u-boot/dtb/modules/blobs from official
stock firmware, build our own rootfs/userspace on top with Buildroot.

## GPU driver reality

- PowerVR GE8300: Mesa's open-source PowerVR driver explicitly lists it as
  "unsupported, not under active development" ([Mesa docs](https://docs.mesa3d.org/drivers/powervr.html)).
- No Panfrost/Lima path applies (those target Mali, not PowerVR).
- Only path to GPU accel is the proprietary blob the Knulli project extracted and packaged.
- **No documented precedent** of Wayland compositors or Electron/Chromium running on GE8300
  hardware. 1GB RAM is already below Chromium's own recommended minimum.
- Note: the H700 SoC (newer Anbernic/muOS devices) has a *different*, Mali-based GPU
  (Mali-G31/G32, Bifrost, Panfrost-capable) — not comparable to the Brick's PowerVR part.
  Don't confuse guidance/precedent for H700 devices with what's possible here.
- Decision: GUI apps (later milestone) use a lightweight webview (Tauri), not Electron.

## Mainline kernel support

Per [linux-sunxi](https://linux-sunxi.org/Linux_Kernel), A133/A133p mainline U-Boot/kernel
support is still in-progress (2024 patchwork), with only watchdog/PMU/DMA/USB/MMC partially
upstreamed. LCD panel, PowerVR GPU, audio codec, WiFi/BT, and PMIC/battery management all
require the vendor Tina/Allwinner BSP kernel — none are mainline-ready as of this research.

## WiFi/Bluetooth driver

A133-family devices pair with **XR829** or **AW859A** WiFi/BT chips
([CNX Software](https://www.cnx-software.com/2020/10/31/allwinner-a133-tablet-processor-pairs-with-xr829-or-aw859a-wifi-bluetooth-chip/)).
Brick spec (802.11b/g/n + BT4.2) is consistent with **XR829**. Driver exists only in the
Tina-Linux/vendor BSP; unofficial out-of-tree mainline ports exist
([Icenowy/xradio](https://github.com/Icenowy/xradio)) but are unmaintained — we use the
vendor BSP module extracted from stock firmware instead, same as the community projects.

## Confirmed: stock firmware container format (reverse-engineered, working extractor)

The `TG3040_Brick_firmware_v1.1.1.zip` release from `trimui/firmware_brick` contains a single
`trimui_tg3040.awimg` (584MB), which is an **Allwinner "IMAGEWTY" container** (v3,
`header_version=0x300`, unencrypted since the magic is plaintext). Fully parsed and validated
with [`firmware-extract/extract_imagewty.py`](../firmware-extract/extract_imagewty.py) —
38 items extracted cleanly, including:

| item | contains |
|---|---|
| `u-boot.fex` | U-Boot (786KB) |
| `boot0_sdcard.fex` | SPL / boot0 for SD boot (64KB) |
| `boot.fex` | **Android bootimg** (`ANDROID!` magic) wrapping the kernel — split with [`parse_bootimg.py`](../firmware-extract/parse_bootimg.py) into a confirmed-valid **ARM64 Linux kernel Image** (11.86MB, `file` identifies it directly) + a near-empty ramdisk (12 bytes — not initramfs-based boot) |
| `sunxi.fex` | device-tree config package (153KB) — contains `sun50iw10`/`allwinner,a133` compatible strings, confirming SoC match |
| `env.fex` | U-Boot environment (128KB) |
| `rootfs.fex` | **ext4** filesystem, 566MB — the real userspace + kernel modules (wifi/bt/gpu). Confirmed via ext4 superblock magic at the right offset. Needs a Linux host to loop-mount; can't be read directly on macOS. |
| `sys_partition.fex` | plaintext partition table — the real on-device partition layout: `bootloader`(49152 sectors) → `env` → `env-redund` → `boot`(49152) → `rootfs`(1146880) → `rootfs_data`(4194304) → `private`(1024) → `recovery`(32768) → `pstore`(1024) → `UDISK`(rest). Sizes are in 512-byte sectors. This is the layout our `genimage.cfg` needs to reproduce so stock u-boot finds our partitions unmodified. |
| `sunxi_gpt.fex` / `sunxi_mbr.fex` | raw GPT/MBR partition table blobs matching the above |

`gh release download` silently truncates these large assets (reports success, writes a partial
file) — use `curl -L` instead (see `fetch_stock_firmware.sh`). Also, macOS/BSD `unzip` can't
extract the `.awimg` because the zip uses LZMA compression (`unzip -l` works, extraction
doesn't) — use Python's `zipfile` module instead (supports LZMA natively).

Working pipeline: `fetch_stock_firmware.sh` → `extract.sh` → `firmware-extract/out/` containing
all 38 raw items + `boot_split/kernel.Image`.

## Bottom line for planning

- Kernel/u-boot/dtb/wifi+bt+gpu modules: extracted binaries from stock `firmware_brick`
  release, not built from source.
- Rootfs/userspace: ours, via Buildroot.
- GPU accel: proprietary blob only, treat as experimental/best-effort for later GUI-app
  milestones (Tauri browser, native games) — not required for the terminal-only base system.
- No emulator exists for this hardware — all boot verification happens on the real device.
