# Test Report

Date: 2026-04-06

## Host Validation

- `qemu-system-x86_64 --version`: pass
- `virt-install --version`: pass
- `virsh list --all`: pass
- `/dev/kvm`: present

## Harness Validation

- `python3 -m py_compile harness_config.py system_agent.py system_agent_trainer.py scripts/qemu_smoke.py`: pass
- `./scripts/release_smoke.sh`: pass
- `./system-agent --print-config`: pass

## VM Smoke Results

### Ubuntu 24.04 LTS

- status: pass
- image: `ubuntu-24.04-minimal-cloudimg-amd64.img`
- result JSON:

```json
{"target":"ubuntu-24.04-lts","status":"passed","image_url":"https://cloud-images.ubuntu.com/minimal/releases/noble/release/ubuntu-24.04-minimal-cloudimg-amd64.img","serial_log":"/home/lil-archy4/.local/share/system-agent-harness/vm-smoke/ubuntu-24.04-lts/serial.log","duration_seconds":22.1}
```

- serial evidence:
  - `Reached target ... Login Prompts`
  - `SYSTEM_AGENT_SMOKE_OK`
  - `Cloud-init ... finished`

### Fedora 43 Cloud

- status: pass
- image: `Fedora-Cloud-Base-Generic-43-1.6.x86_64.qcow2`
- result JSON:

```json
{"target":"fedora-43-cloud","status":"passed","image_url":"https://download.fedoraproject.org/pub/fedora/linux/releases/43/Cloud/x86_64/images/Fedora-Cloud-Base-Generic-43-1.6.x86_64.qcow2","serial_log":"/home/lil-archy4/.local/share/system-agent-harness/vm-smoke/fedora-43-cloud/serial.log","duration_seconds":18.1}
```

- serial evidence:
  - `Reached target ... Login Prompts`
  - `SYSTEM_AGENT_SMOKE_OK`
  - `Cloud-init ... finished`

## Artifacts

- Ubuntu serial log: `/home/lil-archy4/.local/share/system-agent-harness/vm-smoke/ubuntu-24.04-lts/serial.log`
- Fedora serial log: `/home/lil-archy4/.local/share/system-agent-harness/vm-smoke/fedora-43-cloud/serial.log`
- Smoke log: `/home/lil-archy4/.local/share/system-agent-harness/logs/release-smoke-20260406T160746Z.log`

## Notes

- The VM smoke path currently uses direct QEMU with KVM, user-mode networking, a temporary NoCloud seed ISO, and serial sentinel detection.
- Libvirt is installed and functional, but the automated smoke path does not currently depend on a libvirt NAT network.
