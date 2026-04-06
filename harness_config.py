#!/usr/bin/env python3
import json
import os
import time
from pathlib import Path


APP_SLUG = "system-agent-harness"
ROOT = Path(__file__).resolve().parent
HOME = Path.home()
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / APP_SLUG
DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local" / "share")) / APP_SLUG
LOG_DIR = DATA_DIR / "logs"
CONFIG_FILE = CONFIG_DIR / "config.json"
PLAYBOOK_FILE = DATA_DIR / "playbook.json"
PROMPT_MEMORY_FILE = DATA_DIR / "prompt-memory.json"
TRAINER_STATE_FILE = DATA_DIR / "trainer-state.json"
MODEL_DIR = ROOT / "vosk-model-small-en-us-0.15"


def ensure_runtime_dirs():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def default_config():
    return {
        "provider": "codex",
        "use_provider_preset": True,
        "model": "gpt-5.4-mini",
        "trainer_model": "gpt-5.4-mini",
        "working_root": str(HOME),
        "voice": {
            "model_dir": str(MODEL_DIR),
        },
        "ui": {
            "panel_width": 680,
            "prompt_height": 72,
            "send_button_width": 68,
            "top_margin": 96,
            "side_margin": 420,
            "window_radius": 24,
            "prompt_radius": 22,
            "opacity": 0.76,
            "horizontal_align": "center",
            "vertical_align": "top",
        },
        "system_instructions": [
            "You are the local System Agent Harness for this Linux machine.",
            "Fulfill the user's request by directly operating the local system when appropriate.",
            "Use shell commands, local applications, browser automation, file edits, coding tools, git, gh, vercel, and filesystem tools as needed.",
            "Prefer existing local apps and commands over installing new dependencies unless installation is necessary.",
            "If opening graphical apps under Hyprland, prefer `uwsm-app -- <command>` when suitable.",
            "When the task is complex, combine tools instead of using a single-command mindset.",
            "Avoid destructive actions unless the user explicitly asks for them.",
        ],
        "runner": {
            "command": [
                "codex",
                "exec",
                "--skip-git-repo-check",
                "--dangerously-bypass-approvals-and-sandbox",
                "-C",
                "{cwd}",
                "-m",
                "{model}",
                "{prompt}",
            ]
        },
        "trainer": {
            "command": [
                "codex",
                "exec",
                "--skip-git-repo-check",
                "--dangerously-bypass-approvals-and-sandbox",
                "--ephemeral",
                "-C",
                "{cwd}",
                "-m",
                "{trainer_model}",
                "{prompt}",
            ]
        },
        "presets": {
            "codex": {
                "runner": [
                    "codex",
                    "exec",
                    "--skip-git-repo-check",
                    "--dangerously-bypass-approvals-and-sandbox",
                    "-C",
                    "{cwd}",
                    "-m",
                    "{model}",
                    "{prompt}",
                ]
            },
            "claude": {
                "runner": [
                    "claude",
                    "--print",
                    "--dangerously-skip-permissions",
                    "{prompt}",
                ]
            },
            "claude-code": {
                "runner": [
                    "claude",
                    "--print",
                    "--dangerously-skip-permissions",
                    "{prompt}",
                ]
            },
            "chatgpt": {
                "runner": [
                    "chatgpt",
                    "{prompt}",
                ]
            },
            "openai": {
                "runner": [
                    "chatgpt",
                    "{prompt}",
                ]
            },
            "openclaw": {
                "runner": [
                    "openclaw",
                    "run",
                    "--cwd",
                    "{cwd}",
                    "--model",
                    "{model}",
                    "{prompt}",
                ]
            },
            "ollama": {
                "runner": ["ollama", "run", "{model}", "{prompt}"]
            },
            "gemini": {
                "runner": ["gemini", "-p", "{prompt}"]
            },
            "custom": {
                "runner": ["your-agent-command", "--cwd", "{cwd}", "--model", "{model}", "{prompt}"]
            },
        },
    }


def ensure_config():
    ensure_runtime_dirs()
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(default_config(), indent=2))


def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def load_config():
    ensure_config()
    config = load_json(CONFIG_FILE, default_config())
    merged = default_config()
    for key, value in config.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        else:
            merged[key] = value
    provider = merged.get("provider", "codex")
    presets = merged.get("presets", {})
    preset = presets.get(provider)
    if merged.get("use_provider_preset", True) and isinstance(preset, dict):
        if "runner" in preset:
            merged.setdefault("runner", {})["command"] = list(preset["runner"])
        if "trainer" in preset:
            merged.setdefault("trainer", {})["command"] = list(preset["trainer"])
    return merged


def list_provider_names():
    return sorted(load_config().get("presets", {}).keys())


def set_provider(name):
    ensure_config()
    data = load_json(CONFIG_FILE, default_config())
    presets = default_config().get("presets", {})
    if name not in presets:
        raise ValueError(f"unknown provider: {name}")
    data["provider"] = name
    data["use_provider_preset"] = True
    save_json(CONFIG_FILE, data)
    return load_config()


def update_config(patch):
    ensure_config()
    data = load_json(CONFIG_FILE, default_config())
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(data.get(key), dict):
            data[key].update(value)
        else:
            data[key] = value
    save_json(CONFIG_FILE, data)
    return load_config()


def replace_tokens(value, mapping):
    for key, replacement in mapping.items():
        value = value.replace("{" + key + "}", str(replacement))
    return value


def build_command(command_template, mapping):
    return [replace_tokens(str(token), mapping) for token in command_template]


def build_runner_command(prompt, training=False):
    config = load_config()
    working_root = Path(config.get("working_root", str(HOME))).expanduser()
    key = "trainer" if training else "runner"
    command_template = config.get(key, {}).get("command", [])
    mapping = {
        "cwd": str(working_root),
        "model": config.get("model", "gpt-5.4-mini"),
        "trainer_model": config.get("trainer_model", config.get("model", "gpt-5.4-mini")),
        "prompt": prompt,
    }
    return build_command(command_template, mapping)


def append_log(name, payload):
    ensure_runtime_dirs()
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    target = LOG_DIR / f"{timestamp}-{name}.json"
    target.write_text(json.dumps(payload, indent=2))
    return target
