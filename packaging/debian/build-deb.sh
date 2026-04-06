#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="$(cat "$ROOT/VERSION")"
PKGROOT="$ROOT/packaging/debian/pkgroot"
OUT="$ROOT/packaging/debian/commander_${VERSION}_amd64.deb"

rm -rf "$PKGROOT"
mkdir -p "$PKGROOT/DEBIAN" "$PKGROOT/usr/lib/commander" "$PKGROOT/usr/bin" "$PKGROOT/usr/share/commander"

cat > "$PKGROOT/DEBIAN/control" <<EOF
Package: commander
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Lil Archyfour <jaydencrowther@gmail.com>
Depends: python3, python3-gi, python3-vosk, gir1.2-gtk-4.0, gir1.2-adw-1, libgtk4-layer-shell0, pipewire
Description: Wayland overlay AI harness with voice and text control
 Commander is a local Linux launcher with text and voice summon flows,
 configurable AI backends, packaging support, and a background trainer.
EOF

cp -r \
  "$ROOT/harness_config.py" \
  "$ROOT/system_agent.py" \
  "$ROOT/system_agent_trainer.py" \
  "$ROOT/scenarios.json" \
  "$ROOT/release-targets.json" \
  "$ROOT/config.example.json" \
  "$ROOT/README.md" \
  "$ROOT/VERSION" \
  "$ROOT/scripts" \
  "$ROOT/vosk-model-small-en-us-0.15" \
  "$PKGROOT/usr/lib/commander/"

mkdir -p "$PKGROOT/usr/share/commander"
cp -r "$ROOT/packaging/hyprland" "$PKGROOT/usr/share/commander/"
cp -r "$ROOT/packaging/systemd" "$PKGROOT/usr/share/commander/"

install -Dm755 "$ROOT/system-agent" "$PKGROOT/usr/lib/commander/system-agent"
install -Dm755 "$ROOT/system-agent-trainer" "$PKGROOT/usr/lib/commander/system-agent-trainer"
install -Dm755 "$ROOT/commander" "$PKGROOT/usr/bin/commander"
install -Dm755 "$ROOT/commander-trainer" "$PKGROOT/usr/bin/commander-trainer"

dpkg-deb --build --root-owner-group "$PKGROOT" "$OUT"
echo "$OUT"
