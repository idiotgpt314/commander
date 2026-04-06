# Publishing Commander

## Package Manager Path

- Arch users: publish the `PKGBUILD` to AUR after each tagged release.
- Debian and Debian-based users: attach the built `.deb` to each GitHub release.
- Fedora users: keep the RPM spec current and publish through COPR when the release flow is stable.

## Release Order

1. bump `VERSION`
2. tag and publish the GitHub release
3. build and attach `commander_<version>_amd64.deb`
4. build and install the Arch package locally so the maintainer machine matches the release
5. update AUR metadata to the same tag

## Free Distribution

- GitHub Releases is the download source of truth
- AUR provides native Arch install for power users
- `.deb` artifacts cover Ubuntu, Debian, Pop!_OS, Mint, and other Debian-based systems
- later, COPR can cover Fedora without changing the local-first product model
