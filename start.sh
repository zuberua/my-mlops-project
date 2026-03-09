#!/usr/bin/env bash
# Start Mark Vle Strands Agent safely with AWS credentials + stable venv

set -Eeuo pipefail
cd "$(dirname "$0")"

echo "=============================================="
echo "Starting Mark Vle Strands Agent..."
echo "=============================================="

# ======================================================
# 1. CERTIFICATES (keep only if you are in corporate env)
# ======================================================
echo "Exporting certs..."
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/corp-combined-ca.crt
export SSL_CERT_FILE=/etc/ssl/certs/corp-combined-ca.crt
export AWS_CA_BUNDLE=/etc/ssl/certs/corp-combined-ca.crt

# Internal GE Vernova domains bypass proxy
export NO_PROXY=".gevernova.net,dev-gateway.apps.gevernova.net,localhost,127.0.0.1,::1"
export no_proxy="$NO_PROXY"

# ==============================
# 2. AWS CREDENTIAL EXPORT (SAFE)
# ==============================
echo "Exporting AWS credentials from ~/.aws/credentials [default]"

export AWS_ACCESS_KEY_ID="$(aws configure get default.aws_access_key_id)"
export AWS_SECRET_ACCESS_KEY="$(aws configure get default.aws_secret_access_key)"
export AWS_SESSION_TOKEN="$(aws configure get default.aws_session_token)"

: "${AWS_ACCESS_KEY_ID:?ERROR: Missing aws_access_key_id}"
: "${AWS_SECRET_ACCESS_KEY:?ERROR: Missing aws_secret_access_key}"
: "${AWS_SESSION_TOKEN:?ERROR: Missing aws_session_token}"

echo "✓ AWS credentials exported"

export AWS_REGION="${AWS_REGION:-us-east-1}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-$AWS_REGION}"

# ============================================
# 3. PYTHON + VIRTUAL ENVIRONMENT (SELF‑HEALING)
# ============================================

PYBIN="${PYBIN:-python3.13}"
VENV_DIR="venv"
REQ_FILE="requirements.txt"

# --- Create venv if missing ---
if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtual environment with ${PYBIN} ..."
  "${PYBIN}" -m venv "$VENV_DIR"
fi

# --- Activate venv ---
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
echo "✓ Virtual environment activated ($(python -V))"

# --- Self-heal venv if pip launcher is broken or missing ---
if [[ ! -f "${VENV_DIR}/bin/pip" ]] || ! "${VENV_DIR}/bin/pip" --version >/dev/null 2>&1; then
  echo "⚠ pip launcher broken or missing — fixing..."
  # Fix CRLF line endings first
  sed -i 's/\r$//' "${VENV_DIR}/bin/pip" 2>/dev/null || true
  # If still broken, recreate venv
  if ! "${VENV_DIR}/bin/pip" --version >/dev/null 2>&1; then
    echo "  Recreating virtualenv..."
    deactivate || true
    rm -rf "$VENV_DIR"
    "${PYBIN}" -m venv "$VENV_DIR"
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
  fi
fi

# Ensure pip is available (use python -m pip as fallback)
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
    echo "   Press Ctrl+C to stop or wait 5s to continue..."
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

python3 flask_app.py
