#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/system-agent-harness/logs"
mkdir -p "$LOG_DIR"
REPORT="$LOG_DIR/release-smoke-$(date -u +%Y%m%dT%H%M%SZ).log"
cd "$ROOT"

{
  echo "== py_compile =="
  python3 -m py_compile "$ROOT/harness_config.py" "$ROOT/system_agent.py" "$ROOT/system_agent_trainer.py"
  echo
  echo "== config =="
  "$ROOT/.venv/bin/python" "$ROOT/system_agent.py" --print-config
  echo
  echo "== trainer scenarios =="
  "$ROOT/.venv/bin/python" - <<'PY'
from system_agent_trainer import load_scenarios
for scenario in load_scenarios():
    print(f"{scenario['id']}: {scenario['title']}")
PY
  echo
  echo "== qemu availability =="
  command -v qemu-system-x86_64 || echo "qemu-system-x86_64 not installed"
} | tee "$REPORT"

printf '\nReport written to %s\n' "$REPORT"
