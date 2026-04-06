# Commander

Portable Linux overlay launcher and background trainer for local AI-assisted system control.

## What Changed

Commander is no longer hardwired to `codex exec`. It is now a harness with:

- pluggable AI runner commands through `~/.config/system-agent-harness/config.json`
- XDG config and data paths instead of machine-specific hardcoded paths
- prompt frequency memory feeding the trainer
- distro setup artifacts for Ubuntu, Fedora, and Arch
- release smoke scripts and QEMU scaffolding

## Core Behavior

- double tap `Super` for text mode
- hold `Super` for voice capture
- release `Super` to transcribe and submit
- background trainer learns from built-in scenarios plus repeated real prompts

## Runtime Paths

- Config: `~/.config/system-agent-harness/config.json`
- Data: `~/.local/share/system-agent-harness`
- Logs: `~/.local/share/system-agent-harness/logs`

## Hooking Up An AI

Edit `~/.config/system-agent-harness/config.json` and set the `runner.command` array to your AI CLI.

Examples:

`codex`

```json
{
  "provider": "codex",
  "runner": {
    "command": ["codex", "exec", "-C", "{cwd}", "-m", "{model}", "{prompt}"]
  }
}
```

`claude-code`

```json
{
  "provider": "claude-code",
  "runner": {
    "command": ["claude", "--print", "--dangerously-skip-permissions", "{prompt}"]
  }
}
```

`openclaw`

```json
{
  "provider": "openclaw",
  "runner": {
    "command": ["openclaw", "run", "--cwd", "{cwd}", "--model", "{model}", "{prompt}"]
  }
}
```

`ollama`

```json
{
  "provider": "ollama",
  "runner": {
    "command": ["ollama", "run", "{model}", "{prompt}"]
  }
}
```

Any custom CLI can be used as long as it accepts a prompt through the command array.

## Install

Run:

```bash
./install.sh
```

That script:

- bootstraps the virtualenv
- installs Python dependencies
- creates the default harness config
- prints suggested distro-specific system dependency commands

## Release Targets

See [release-targets.json](/home/lil-archy4/Work/system-agent/release-targets.json).

First-wave targets:

- Ubuntu 24.04 LTS
- Fedora Cloud 43
- Arch Linux host install

## Packaging Artifacts

- Hyprland snippet: [system-agent.conf](/home/lil-archy4/Work/system-agent/packaging/hyprland/system-agent.conf)
- User service: [system-agent.service](/home/lil-archy4/Work/system-agent/packaging/systemd/system-agent.service)
- Trainer service: [system-agent-trainer.service](/home/lil-archy4/Work/system-agent/packaging/systemd/system-agent-trainer.service)

## Testing

Local release smoke:

```bash
./scripts/release_smoke.sh
```

QEMU scaffold:

```bash
./scripts/qemu_smoke.py --dry-run
```

The QEMU script currently validates host readiness and target selection. Full boot automation still depends on host QEMU packages and image acquisition.

## Packaging

- Arch/AUR source package: [PKGBUILD](/home/lil-archy4/Work/system-agent/packaging/arch/PKGBUILD)
- Release notes: [RELEASING.md](/home/lil-archy4/Work/system-agent/packaging/RELEASING.md)
