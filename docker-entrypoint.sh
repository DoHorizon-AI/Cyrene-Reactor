#!/bin/bash
set -euo pipefail

DATA_DIR="${CYRENE_DATA_DIR:-/data}"
mkdir -p "${DATA_DIR}/credentials" "${DATA_DIR}/certs" "${DATA_DIR}/config"
chmod 700 "${DATA_DIR}/credentials"

# If arguments are passed, handle them
if [ $# -gt 0 ]; then
    if [[ "$1" == -* ]]; then
        exec cyrene-reactor control "$@"
    else
        exec "$@"
    fi
fi

# 1. Initialize control credentials if not present
if [ ! -f "${DATA_DIR}/credentials/control.token" ]; then
    echo "[entrypoint] Initializing Reactor control secrets..."
    cyrene-reactor init-secrets --config "${DATA_DIR}/credentials"
    chmod 600 "${DATA_DIR}/credentials/control.token"
fi

# 2. Ensure engine binding token exists with strict permissions (>= 32 chars, mode 0600)
if [ ! -f "${DATA_DIR}/credentials/engine.token" ]; then
    python3 -c "import secrets; print(secrets.token_urlsafe(48))" > "${DATA_DIR}/credentials/engine.token"
    chmod 600 "${DATA_DIR}/credentials/engine.token"
fi

# 3. Generate self-signed TLS certificates for remote listener if missing
if [ ! -f "${DATA_DIR}/certs/tls.crt" ] || [ ! -f "${DATA_DIR}/certs/tls.key" ]; then
    echo "[entrypoint] Generating self-signed TLS certificate for Reactor controller..."
    openssl req -x509 -newkey rsa:2048 -nodes \
        -keyout "${DATA_DIR}/certs/tls.key" \
        -out "${DATA_DIR}/certs/tls.crt" \
        -days 3650 \
        -subj "/CN=cyrene-reactor" 2>/dev/null
    chmod 600 "${DATA_DIR}/certs/tls.key"
fi

# 4. Generate default control.json if missing
CONFIG_FILE="${DATA_DIR}/config/control.json"
if [ ! -f "${CONFIG_FILE}" ]; then
    echo "[entrypoint] Generating default ${CONFIG_FILE}..."
    cat <<EOF > "${CONFIG_FILE}"
{
  "database_path": "${DATA_DIR}/reactor.sqlite3",
  "credential_file": "${DATA_DIR}/credentials/control.token",
  "public_base_url": "${CYRENE_PUBLIC_BASE_URL:-https://localhost:19300}",
  "serving_bindings": [
    {
      "binding_id": "default",
      "control_url": "${CYRENE_SERVING_CONTROL_URL:-http://127.0.0.1:8001}",
      "credential_file": "${DATA_DIR}/credentials/engine.token"
    }
  ],
  "exchange_receivers": []
}
EOF
fi

HOST="${REACTOR_HOST:-0.0.0.0}"
PORT="${REACTOR_PORT:-19300}"

if [ "${REACTOR_ENABLE_TLS:-false}" = "true" ]; then
    echo "[entrypoint] Starting Cyrene Reactor controller on ${HOST}:${PORT} (TLS enabled)..."
    exec cyrene-reactor control \
        --config "${CONFIG_FILE}" \
        --host "${HOST}" \
        --port "${PORT}" \
        --tls-certificate "${DATA_DIR}/certs/tls.crt" \
        --tls-key "${DATA_DIR}/certs/tls.key"
else
    echo "[entrypoint] Starting Cyrene Reactor controller on ${HOST}:${PORT} (plain HTTP)..."
    export CYRENE_INSECURE_HTTP="1"
    exec cyrene-reactor control \
        --config "${CONFIG_FILE}" \
        --host "${HOST}" \
        --port "${PORT}"
fi
