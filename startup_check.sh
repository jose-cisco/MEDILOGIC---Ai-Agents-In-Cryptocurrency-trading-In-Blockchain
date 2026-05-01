#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_DIR="$BACKEND_DIR/.venv311"

echo "=== Production Readiness Check (GLM-5.1 + Grok) ==="
echo "Root: $ROOT_DIR"

if ! command -v python3.11 >/dev/null 2>&1; then
  echo "[ERROR] python3.11 not found. Install Python 3.11 first."
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "[INFO] Creating Python 3.11 virtualenv at $VENV_DIR"
  python3.11 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo "[INFO] Installing backend dependencies"
pip install -q --upgrade pip
pip install -q -r "$BACKEND_DIR/requirements.txt"

if [ ! -f "$BACKEND_DIR/.env" ]; then
  echo "[ERROR] backend/.env not found. Copy backend/.env.example to backend/.env first."
  exit 1
fi

echo "[INFO] Validating strict environment rules"
PYTHONPATH="$BACKEND_DIR" python - <<'PY'
from app.core.config import get_settings

settings = get_settings()
settings.validate_runtime()
print(f"[OK] Environment validated. TRADING_MODE={settings.TRADING_MODE}")
print(f"[OK] Provider target={settings.LLM_PROVIDER}")
PY

echo "[INFO] Running smoke tests"
PYTHONPATH="$BACKEND_DIR" pytest -q "$BACKEND_DIR/tests/test_smoke_api.py"

echo "[INFO] Starting temporary API server for endpoint checks"
PYTHONPATH="$BACKEND_DIR" uvicorn app.main:app --host 127.0.0.1 --port 8000 >/tmp/ai_agent_startup_check.log 2>&1 &
SERVER_PID=$!
cleanup() {
  kill "$SERVER_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 3

echo "[INFO] Checking /status/system"
curl -fsS "http://127.0.0.1:8000/api/v1/status/system" >/tmp/status_system.json
echo "[OK] /status/system reachable"

echo "[INFO] Checking /backtest/strategies"
curl -fsS "http://127.0.0.1:8000/api/v1/backtest/strategies" >/tmp/backtest_strategies.json
echo "[OK] /backtest/strategies reachable"

echo "[INFO] Checking /trading/analyze"
curl -fsS -X POST "http://127.0.0.1:8000/api/v1/trading/analyze" >/tmp/trading_analyze.json
echo "[OK] /trading/analyze reachable"

echo ""
echo "=== Startup check passed ==="
echo "Log file: /tmp/ai_agent_startup_check.log"
echo "You can now run the full system with: ./start.sh"
