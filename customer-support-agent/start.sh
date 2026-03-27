#!/bin/bash
set -e

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=== Mark VIe Programming Agent ===${NC}"

# Kill any existing process on port 8001
lsof -ti:8001 2>/dev/null | xargs kill -9 2>/dev/null || true

# ---- Backend ----
echo -e "${GREEN}[1/3] Setting up Python venv...${NC}"
if [ ! -d "venv" ]; then
    python3.13 -m venv venv
fi
source venv/bin/activate

echo -e "${GREEN}[2/3] Upgrading pip and installing deps...${NC}"
pip install --upgrade pip
pip install -q -r requirements.txt

echo -e "${GREEN}[3/3] Starting backend on :8001...${NC}"
PYTHONPATH="$PROJECT_DIR" uvicorn agent.backend.app:app --reload --port 8001 &
BACKEND_PID=$!

# ---- Frontend ----
if command -v npm &>/dev/null; then
    echo -e "${GREEN}[4/4] Starting frontend on :3000...${NC}"
    cd agent/frontend
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    REACT_APP_API_URL=http://localhost:8001 npm start &
    FRONTEND_PID=$!
    cd "$PROJECT_DIR"
    echo -e "${BLUE}Frontend: http://localhost:3000${NC}"
else
    echo -e "${RED}npm not found. Install Node.js to run the frontend:${NC}"
    echo -e "${RED}  brew install node${NC}"
    echo -e "${RED}Then run: cd frontend && npm install && npm start${NC}"
    FRONTEND_PID=""
fi

echo ""
echo -e "${BLUE}Backend:  http://localhost:8001${NC}"
echo -e "${BLUE}Press Ctrl+C to stop.${NC}"

cleanup() {
    kill $BACKEND_PID 2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null
    exit
}
trap cleanup INT TERM
wait
