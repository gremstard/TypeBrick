#!/usr/bin/env bash
# Downloads the latest TrimUI Brick stock firmware release (trimui/firmware_brick).
#
# NOTE: `gh release download` truncates these large assets somewhere in its
# pagination/redirect handling (confirmed empirically: reports success but
# writes a partial file). Use plain `curl -L` instead, which downloads correctly.
set -euo pipefail

REPO="trimui/firmware_brick"
OUT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/downloads"
mkdir -p "$OUT_DIR"

TAG="$(gh release list --repo "$REPO" --json tagName,isLatest --jq '.[] | select(.isLatest) | .tagName')"
ASSET="$(gh release view "$TAG" --repo "$REPO" --json assets --jq '.assets[] | select(.name | endswith(".zip") and (contains("firmware"))) | .name')"

echo "Latest release: $TAG"
echo "Asset: $ASSET"

DEST="$OUT_DIR/$ASSET"
if [[ -f "$DEST" ]]; then
    echo "Already downloaded: $DEST"
else
    URL="https://github.com/$REPO/releases/download/$TAG/$ASSET"
    curl -L -o "$DEST.partial" "$URL"
    mv "$DEST.partial" "$DEST"
fi

EXPECTED_SIZE="$(gh release view "$TAG" --repo "$REPO" --json assets --jq ".assets[] | select(.name==\"$ASSET\") | .size")"
ACTUAL_SIZE="$(stat -f%z "$DEST" 2>/dev/null || stat -c%s "$DEST")"
if [[ "$EXPECTED_SIZE" != "$ACTUAL_SIZE" ]]; then
    echo "ERROR: size mismatch (expected $EXPECTED_SIZE, got $ACTUAL_SIZE) - re-download" >&2
    exit 1
fi

echo "$DEST" > "$OUT_DIR/.latest_firmware_zip"
echo "OK: $DEST ($ACTUAL_SIZE bytes)"
