#!/usr/bin/env python3
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from harness_config import (
    PLAYBOOK_FILE,
    PROMPT_MEMORY_FILE,
    ROOT,
    TRAINER_STATE_FILE,
    append_log,
    build_runner_command,
    ensure_config,
    load_config,
)


SCENARIOS_FILE = ROOT / "scenarios.json"
MIN_SCENARIO_INTERVAL = 60 * 60 * 6
LOOP_INTERVAL = 60 * 30
MAX_DYNAMIC_SCENARIOS = 8


def read_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2))


def load_scenarios():
    scenarios = list(read_json(SCENARIOS_FILE, {"scenarios": []}).get("scenarios", []))
    return scenarios + load_frequent_prompt_scenarios()


def prompt_to_scenario_id(normalized_prompt):
    slug = "".join(ch if ch.isalnum() else "-" for ch in normalized_prompt)[:48].strip("-")
    return f"frequent-{slug or 'prompt'}"


def load_frequent_prompt_scenarios():
    data = read_json(PROMPT_MEMORY_FILE, {"prompts": []})
    scenarios = []
    for item in data.get("prompts", []):
        count = int(item.get("count", 0))
        example = item.get("example", "").strip()
        normalized = item.get("normalized", "").strip()
        if count < 2 or not example or not normalized:
            continue
        scenarios.append(
            {
                "id": prompt_to_scenario_id(normalized),
                "category": "frequent-task",
                "title": f"Frequent task: {example[:72]}",
                "prompt": example,
                "priority": count,
                "source": "prompt-memory",
            }
        )
    scenarios.sort(key=lambda item: item.get("priority", 0), reverse=True)
    return scenarios[:MAX_DYNAMIC_SCENARIOS]


def load_state():
    return read_json(TRAINER_STATE_FILE, {"runs": {}, "last_index": -1})


def save_state(data):
    write_json(TRAINER_STATE_FILE, data)


def load_playbook():
    return read_json(PLAYBOOK_FILE, {"lessons": []})


def save_playbook(data):
    write_json(PLAYBOOK_FILE, data)


def choose_scenario():
    scenarios = load_scenarios()
    if not scenarios:
        return None

    state = load_state()
    now = time.time()

    for offset in range(len(scenarios)):
        index = (state.get("last_index", -1) + 1 + offset) % len(scenarios)
        scenario = scenarios[index]
        last_run = state.get("runs", {}).get(scenario["id"], 0)
        if now - last_run >= MIN_SCENARIO_INTERVAL:
            state["last_index"] = index
            save_state(state)
            return scenario

    return None


def build_training_prompt(scenario):
    priority = scenario.get("priority")
    return "\n".join(
        [
            "You are training a local system agent on the best way to fulfill desktop and coding tasks on this Linux Hyprland machine.",
            "Optimize for speed, safety, tool choice, and reliable verification.",
            "Return JSON only with keys:",
            "title, best_agent_profile, best_tool_pack, strategy, steps, verification, cautions",
            "Constraints:",
            "- steps, verification, cautions must be arrays of short strings",
            "- no markdown",
            "- no commentary outside JSON",
            f"Scenario title: {scenario['title']}",
            f"Scenario category: {scenario.get('category', 'general')}",
            f"Scenario prompt: {scenario['prompt']}",
            f"Scenario source: {scenario.get('source', 'static-library')}",
            f"Observed frequency: {priority}" if priority is not None else "Observed frequency: unknown",
            "Machine context: Hyprland, codex CLI, gh, vercel, browser automation, full filesystem, voice launcher.",
        ]
    )


def run_training(scenario):
    prompt = build_training_prompt(scenario)
    cmd = build_runner_command(prompt, training=True)

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    raw = result.stdout

    if result.returncode != 0:
        raise RuntimeError(f"codex exec failed: {result.stdout[-800:]}")

    try:
        lesson = json.loads(raw)
    except Exception as err:
        raise RuntimeError(f"trainer returned non-JSON: {err}; raw={raw[:800]}")

    lesson["scenario_id"] = scenario["id"]
    lesson["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    lesson["source_prompt"] = scenario["prompt"]
    lesson["scenario_source"] = scenario.get("source", "static-library")
    if scenario.get("priority") is not None:
        lesson["observed_frequency"] = scenario["priority"]
    return lesson


def merge_lesson(lesson):
    playbook = load_playbook()
    lessons = playbook.get("lessons", [])
    updated = False
    for idx, existing in enumerate(lessons):
        if existing.get("scenario_id") == lesson["scenario_id"]:
            lessons[idx] = lesson
            updated = True
            break
    if not updated:
        lessons.append(lesson)
    lessons.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    playbook["lessons"] = lessons[:24]
    playbook["last_trained_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_playbook(playbook)


def record_run(scenario_id):
    state = load_state()
    state.setdefault("runs", {})[scenario_id] = time.time()
    save_state(state)


def train_one():
    scenario = choose_scenario()
    if not scenario:
        return False
    append_log("trainer-scenario", scenario)
    lesson = run_training(scenario)
    merge_lesson(lesson)
    record_run(scenario["id"])
    return True


def run_daemon():
    while True:
        try:
            trained = train_one()
            time.sleep(LOOP_INTERVAL if trained else 300)
        except Exception:
            time.sleep(300)


def main():
    ensure_config()
    if "--once" in os.sys.argv[1:]:
        train_one()
        return
    run_daemon()


if __name__ == "__main__":
    main()
