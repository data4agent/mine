#!/usr/bin/env bash
set -euo pipefail

INSTALL_PROFILE="${INSTALL_PROFILE:-full}"
VENV_DIR="${VENV_DIR:-.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

check_host_dependencies() {
  "$PYTHON_BIN" scripts/host_diagnostics.py --json >/tmp/mine-host-diagnostics.json || true
}

install_requirements() {
  "$VENV_DIR/bin/python" -m pip install -r requirements-core.txt
  if [[ "$INSTALL_PROFILE" == "browser" || "$INSTALL_PROFILE" == "full" ]]; then
    "$VENV_DIR/bin/python" -m pip install -r requirements-browser.txt
  fi
  if [[ "$INSTALL_PROFILE" == "full" ]]; then
    "$VENV_DIR/bin/python" -m pip install -r requirements-dev.txt
  fi
}

if [[ -d "$VENV_DIR" ]]; then
  echo "reusing existing virtualenv: $VENV_DIR"
else
  uv venv --seed "$VENV_DIR"
fi

check_host_dependencies
install_requirements
"$VENV_DIR/bin/python" scripts/verify_env.py --profile "$INSTALL_PROFILE"
"$VENV_DIR/bin/python" scripts/smoke_test.py
