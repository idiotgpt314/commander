# Debian Packaging Notes

Target package name: `commander`

Recommended first path:

1. Use `fpm` or `dh-virtualenv` only if you decide to bundle Python runtime pieces.
2. Prefer native distro dependencies for:
   - `python3`
   - `python3-gi`
   - `python3-vosk`
   - `gir1.2-gtk-4.0`
   - `gir1.2-adw-1`
   - `libgtk4-layer-shell0`
   - `pipewire`
3. Install the app into `/usr/lib/commander` and ship wrapper binaries as:
   - `/usr/bin/commander`
   - `/usr/bin/commander-trainer`

The Arch package is the current source-of-truth release layout.
