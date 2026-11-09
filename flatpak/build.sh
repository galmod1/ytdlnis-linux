#!/bin/sh
# Build and install the Flatpak for the current user (no sudo).
set -e
cd "$(dirname "$0")/.."
mkdir -p builddir
flatpak run org.flatpak.Builder --force-clean --user --install-deps-from=flathub \
  --install builddir flatpak/org.galmod.ytdlnis.linux.yaml
echo "Done: flatpak run org.galmod.ytdlnis.linux"
