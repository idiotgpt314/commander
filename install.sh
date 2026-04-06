#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DISTRO_ID=""
if [[ -f /etc/os-release ]]; then
  . /etc/os-release
  DISTRO_ID="${ID:-}"
fi

install_cmd=""
case "$DISTRO_ID" in
  arch)
    install_cmd="sudo pacman -S --needed python python-pip python-gobject gtk4 libadwaita gtk4-layer-shell pipewire"
    ;;
  ubuntu|debian)
    install_cmd="sudo apt update && sudo apt install -y python3 python3-venv python3-pip python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 libgtk4-layer-shell0 pipewire"
    ;;
  fedora)
    install_cmd="sudo dnf install -y python3 python3-pip python3-gobject gtk4 libadwaita gtk4-layer-shell pipewire"
    ;;
esac

if [[ -n "$install_cmd" ]]; then
  printf 'Suggested system dependency command for %s:\n%s\n\n' "${DISTRO_ID:-unknown}" "$install_cmd"
else
  printf 'No distro-specific system dependency command is bundled for this host.\n\n'
fi

python3 -m venv .venv
.venv/bin/pip install --upgrade pip wheel
.venv/bin/pip install -r requirements.txt
./system-agent --init-config >/dev/null

cat <<EOF
Harness bootstrap complete.

Next steps:
1. Edit ~/.config/system-agent-harness/config.json
2. Pick a runner command for your AI provider
3. Launch with: $SCRIPT_DIR/system-agent --show
EOF
