# TypeBrick

A custom Linux build for the [TrimUI Brick](https://trimui.net/) handheld, turning it into a
terminal-first pocket computer. First real milestone: boot, and work as a basic electronic
typewriter (read/write text files, nothing else). Longer term: a nice `cd`/`mkdir`/editor-style
shell, native `ts` (web browser/search/YouTube) and `impv` (block-character image/video
renderer) tools, Claude Code, WiFi + Bluetooth (keyboard works over the top USB-C host port or
BT), and — later — a couple of genuinely non-headless apps (lightweight webview browser,
native/Portmaster games) launched full-screen from the shell.

See [docs/RESEARCH.md](docs/RESEARCH.md) for hardware/firmware background — short version:
TrimUI doesn't publish kernel/u-boot source, so we extract the kernel, u-boot, device tree,
and WiFi/BT/GPU kernel modules from TrimUI's official stock firmware releases (same approach
MinUI/NextUI/Knulli use) and build our own rootfs on top with Buildroot.

## Status

**Milestone 1 in progress**: boot to a basic typewriter (read/write text, nothing else), with:
- Power button: single click = sleep (screen off), auto shutdown after 5 min asleep, double
  click = shutdown
- First-boot wizard: if WiFi isn't connected or a Bluetooth keyboard isn't paired, prompts to
  connect both via D-pad/buttons before continuing
- USB + Bluetooth keyboard input, WiFi online

No custom shell commands beyond the typewriter, ts/impv, Claude Code, or GUI apps yet — those
are follow-up milestones once this is confirmed working on real hardware.

A stock-firmware repack (`output/trimui-brick-stock-repack.img`, built from
`firmware-extract/build_stock_repack_img.py`) already validated the extraction pipeline's
boot0/TOC/GPT offsets on real hardware before any custom work started.

## Layout

```
docs/RESEARCH.md            hardware/firmware findings
firmware-extract/           scripts to pull kernel/u-boot/dtb/modules from stock firmware,
                             plus the stock-repack validation image builder
buildroot-external/         Buildroot external tree (board config, rootfs overlay, image assembly)
overlay/                    rootfs overlay (init, shell profile, config files)
build.sh                    top-level build: extract firmware -> buildroot -> .img
```

## Building

```bash
./build.sh
```

Produces `output/images/typebrick.img`. Flash to a microSD with Balena Etcher or `dd` and
boot the Brick from it. Releases (prebuilt `.img` files) are published on the
[GitHub releases page](https://github.com/gremstard/TypeBrick/releases).

## Hardware

- SoC: Allwinner A133p, quad-core Cortex-A53, 1GB RAM
- Display: 3.2" IPS, ~640x480
- GPU: Imagination PowerVR GE8300 (proprietary driver only, see research doc)
- WiFi/BT: XR829
- Ports: 2x USB-C (bottom = charge/OTG data, top = USB host), headphone jack, microSD
