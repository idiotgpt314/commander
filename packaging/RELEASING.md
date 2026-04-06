# Releasing Commander

## GitHub

1. Push the repo to `https://github.com/idiotgpt314/commander`
2. Tag releases as `vX.Y.Z`
3. Create a GitHub release for each tag

## Arch

What you can self-publish immediately:

- A local pacman package built from `packaging/arch/PKGBUILD`
- An AUR package named `commander` if that name is still free on AUR

What you cannot directly self-publish:

- The official Arch `extra` repository. That requires Arch package maintainer sponsorship and review.

## Local Machine Sync

This machine should run the packaged command paths:

- `/usr/bin/commander`
- `/usr/bin/commander-trainer`

That way the active install matches the packaged release rather than the workspace checkout.

## Other Package Managers

Prepared scaffolds:

- Debian notes: `packaging/debian/README.md`
- RPM spec: `packaging/rpm/commander.spec`

Recommended next public targets after Arch/AUR:

1. Fedora COPR
2. Debian/Ubuntu `.deb`
3. openSUSE OBS
