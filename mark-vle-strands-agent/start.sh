#!/usr/bin/env bash
# Start Mark Vle Strands Agent with AWS credentials + stable venv

set -Eeuo pipefail
cd "$(dirname "$0")"

echo "=============================================="
echo "Starting Mark Vle Strands Agent..."
echo "=============================================="

# ==============================
# 1. LOAD ENVIRONMENT CONFIG
# ==============================
ENV_FILE="config/.env"
if [ -f "$ENV_FILE" ]; then
    echo "Loading config from $ENV_FILE..."
    set -a
    source "$ENV_FILE"
    set +a
    echo "✓ Config loaded"
else
    echo "⚠ No $ENV_FILE found; using defaults"
fi

# ==============================
# 2. AWS CREDENTIALS
# ==============================
AWS_PROFILE="${AWS_PROFILE:-zuberua-Admin}"
export AWS_REGION="${AWS_REGION:-us-west-2}"
export AWS_DEFAULT_REGION="$AWS_REGION"

echo "Exporting AWS credentials from profile: $AWS_PROFILE"
eval $(aws configure export-credentials --profile "$AWS_PROFILE" --format env 2>&1)

if [ -z "${AWS_ACCESS_KEY_ID:-}" ]; then
    echo "✗ Failed to export AWS credentials from profile: $AWS_PROFILE"
    echo "  Run: aws sso login --profile $AWS_PROFILE"
    exit 1
fi
echo "✓ AWS credentials exported"

# ============================================
# 3. PYTHON + VIRTUAL ENVIRONMENT (SELF-HEALING)
# ============================================
PYBIN="${PYBIN:-python3.13}"
VENV_DIR="venv"
REQ_FILE="requirements.txt"

# --- Create venv if missing ---
if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment with ${PYBIN}..."
    "${PYBIN}" -m venv "$VENV_DIR"
fi

# --- Activate venv ---
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
echo "✓ Virtual environment activated ($(python -V))"

# --- Self-heal venv if pip launcher is broken/missing ---
if [[ ! -f "${VENV_DIR}/bin/pip" ]]; then
    echo "⚠ pip launcher missing — recreating virtualenv..."
    deactivate || true
    rm -rf "$VENV_DIR"
    "${PYBIN}" -m venv "$VENV_DIR"
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
fi

# Ensure pip is available
python -m ensurepip --upgrade >/dev/null 2>&1 || true

# ==========================
# 4. INSTALL DEPENDENCIES
# ==========================
if [[ -f "$REQ_FILE" ]]; then
    echo "Upgrading pip..."
    python -m pip install --upgrade pip >/dev/null

    echo "Installing dependencies from ${REQ_FILE}..."
    python -m pip install -r "$REQ_FILE"
else
    echo "⚠ No ${REQ_FILE} found; skipping dependency install."
fi

# ================================
# 5. OPTIONAL: TEST AWS CONNECTIVITY
# ================================
if [[ -f "test_aws_access.py" ]]; then
    echo ""
    echo "Running AWS access test..."
    if ! python test_aws_access.py; then
        echo ""
        echo "⚠ AWS access test failed. The app may not work correctly."
        echo "  Press Ctrl+C to stop or wait 5s to continue..."
        sleep 5
    fi
fi

# ==========================
# 6. START FLASK APPLICATION
# ==========================
echo ""
echo "🚀 Starting Flask on http://localhost:5001"
echo "Press Ctrl+C to stop"
echo ""

python flask_app.py
