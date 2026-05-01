#!/bin/bash
set -e

echo "=== AI Agent Blockchain Trading System ==="
echo "Based on: Karim et al. (2025) - AI Agents Meet Blockchain Survey"
echo "LLM: Ollama GLM-5 | Framework: LangGraph + LangChain | Chains: Ethereum + Solana"
echo "Tip: run ./startup_check.sh first for production-readiness validation"
echo ""

cd "$(dirname "$0")"

check_ollama() {
    if command -v ollama &> /dev/null; then
        echo "[OK] Ollama found"
        if ollama list | grep -q "glm-5"; then
            echo "[OK] GLM-5 model available"
        else
            echo "[!] GLM-5 model not found. Pulling..."
            ollama pull glm-5
        fi
    else
        echo "[ERROR] Ollama not installed. Install from https://ollama.ai"
        echo "        Then run: ollama pull glm-5"
        exit 1
    fi
}

start_backend() {
    echo ""
    echo "--- Starting Backend (FastAPI) ---"
    cd backend
    if [ ! -d "venv" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install -q -r requirements.txt 2>/dev/null || pip install -r requirements.txt
    echo "Starting FastAPI server on http://localhost:8000"
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    cd ..
}

start_frontend() {
    echo ""
    echo "--- Starting Frontend (React + Vite) ---"
    cd frontend
    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies..."
        npm install
    fi
    echo "Starting Vite dev server on http://localhost:3000"
    npm run dev &
    FRONTEND_PID=$!
    cd ..
}

check_ollama

start_backend
start_frontend

echo ""
echo "=== System Running ==="
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Services stopped.'; exit 0" INT TERM

wait