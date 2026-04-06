#!/usr/bin/env python3
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS_FILE = ROOT / "release-targets.json"
DEFAULT_WORKDIR = Path.home() / ".local" / "share" / "system-agent-harness" / "vm-smoke"
SENTINEL = "SYSTEM_AGENT_SMOKE_OK"


def load_targets():
    return json.loads(TARGETS_FILE.read_text()).get("targets", [])


def resolve_image_url(target):
    target_id = target["id"]
    if target_id == "ubuntu-24.04-lts":
        return "https://cloud-images.ubuntu.com/minimal/releases/noble/release/ubuntu-24.04-minimal-cloudimg-amd64.img"
    if target_id == "fedora-43-cloud":
        return "https://download.fedoraproject.org/pub/fedora/linux/releases/43/Cloud/x86_64/images/Fedora-Cloud-Base-Generic-43-1.6.x86_64.qcow2"
    raise ValueError(f"no image url for target {target_id}")


def ensure_tool(name):
    if shutil.which(name) is None:
        raise RuntimeError(f"required tool missing: {name}")


def ensure_download(url, target):
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl", "-fL", "--progress-bar", "-o", str(target), url], check=True)
    return target


def write_text(path, content):
    path.write_text(content, encoding="utf-8")


def create_seed_iso(workdir, hostname):
    seed_dir = workdir / "seed"
    seed_dir.mkdir(parents=True, exist_ok=True)
    user_data = """#cloud-config
users:
  - default
ssh_pwauth: false
disable_root: true
bootcmd:
  - [ sh, -c, 'echo SYSTEM_AGENT_SMOKE_BOOT >/dev/ttyS0' ]
runcmd:
  - [ sh, -c, 'echo SYSTEM_AGENT_SMOKE_OK >/dev/ttyS0' ]
power_state:
  mode: poweroff
  timeout: 10
"""
    meta_data = f"instance-id: {hostname}\nlocal-hostname: {hostname}\n"
    write_text(seed_dir / "user-data", user_data)
    write_text(seed_dir / "meta-data", meta_data)
    iso_path = workdir / "seed.iso"
    subprocess.run(
        [
            "xorriso",
            "-as",
            "mkisofs",
            "-V",
            "cidata",
            "-o",
            str(iso_path),
            str(seed_dir / "user-data"),
            str(seed_dir / "meta-data"),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return iso_path


def create_overlay(base_image, overlay_path):
    if overlay_path.exists():
        overlay_path.unlink()
    subprocess.run(
        [
            "qemu-img",
            "create",
            "-f",
            "qcow2",
            "-F",
            "qcow2",
            "-b",
            str(base_image),
            str(overlay_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    return overlay_path


def run_smoke(target, workdir, timeout_s):
    ensure_tool("qemu-system-x86_64")
    ensure_tool("qemu-img")
    ensure_tool("xorriso")
    image_url = resolve_image_url(target)
    target_dir = workdir / target["id"]
    target_dir.mkdir(parents=True, exist_ok=True)
    base_name = Path(image_url).name
    base_image = ensure_download(image_url, target_dir / base_name)
    overlay = create_overlay(base_image, target_dir / "overlay.qcow2")
    seed = create_seed_iso(target_dir, hostname=target["id"])
    serial_log = target_dir / "serial.log"
    if serial_log.exists():
        serial_log.unlink()

    cmd = [
        "qemu-system-x86_64",
        "-accel",
        "kvm",
        "-cpu",
        "host",
        "-m",
        "2048",
        "-smp",
        "2",
        "-nographic",
        "-display",
        "none",
        "-serial",
        f"file:{serial_log}",
        "-device",
        "virtio-net-pci,netdev=n1",
        "-netdev",
        "user,id=n1",
        "-drive",
        f"if=virtio,format=qcow2,file={overlay}",
        "-drive",
        f"file={seed},format=raw,media=cdrom",
        "-no-reboot",
    ]

    started = time.time()
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    success = False
    try:
        while time.time() - started < timeout_s:
            if serial_log.exists():
                text = serial_log.read_text(errors="ignore")
                if SENTINEL in text:
                    success = True
                    break
            if proc.poll() is not None:
                break
            time.sleep(2)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=20)

    status = "passed" if success else "failed"
    return {
        "target": target["id"],
        "status": status,
        "image_url": image_url,
        "serial_log": str(serial_log),
        "duration_seconds": round(time.time() - started, 1),
    }


def print_dry_run(target):
    print(f"[target] {target['id']}")
    print(f"  image source: {resolve_image_url(target)}")
    print("  boot mode: qemu + kvm + cloud-init serial sentinel")


def main():
    parser = argparse.ArgumentParser(description="Smoke-test supported distro targets in QEMU.")
    parser.add_argument("--target", action="append", help="Target id from release-targets.json")
    parser.add_argument("--dry-run", action="store_true", help="Print planned VM commands without booting")
    parser.add_argument("--timeout", type=int, default=420, help="Per-target timeout in seconds")
    parser.add_argument("--workdir", default=str(DEFAULT_WORKDIR), help="Directory for downloaded images and logs")
    args = parser.parse_args()

    if shutil.which("qemu-system-x86_64") is None:
        print("qemu-system-x86_64 is not installed on the host", file=sys.stderr)
        return 2

    selected = set(args.target or [])
    targets = [
        target
        for target in load_targets()
        if target.get("vm_smoke_ready") and (not selected or target.get("id") in selected)
    ]
    if not targets:
        print("No VM-ready targets selected", file=sys.stderr)
        return 1

    workdir = Path(args.workdir).expanduser()
    workdir.mkdir(parents=True, exist_ok=True)
    results = []
    for target in targets:
        if args.dry_run:
            print_dry_run(target)
            continue
        result = run_smoke(target, workdir, args.timeout)
        results.append(result)
        print(json.dumps(result))

    if args.dry_run:
        return 0
    failed = [item for item in results if item["status"] != "passed"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
