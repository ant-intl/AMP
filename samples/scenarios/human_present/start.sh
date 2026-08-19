#!/usr/bin/env bash
set -eu

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
readonly LOG_DIR="$SCRIPT_DIR/.logs"
mkdir -p "$LOG_DIR"

# ---------------------------------------------------------------------------
# Python interpreter: prefer project venv, fall back to system python3,
#                     then try to install via Homebrew
# ---------------------------------------------------------------------------
if [ -x "$PROJECT_ROOT/.venv/bin/python3" ]; then
  PYTHON="$PROJECT_ROOT/.venv/bin/python3"
elif [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
  PYTHON="$PROJECT_ROOT/.venv/bin/python"
elif command -v python3 &>/dev/null; then
  PYTHON="python3"
elif command -v brew &>/dev/null; then
  echo "python3 not found. Installing via Homebrew..."
  brew install python@3.13
  PYTHON="$(brew --prefix python@3.13)/bin/python3"
else
  echo "ERROR: python3 not found and Homebrew is not installed." >&2
  echo "Please install Python 3.10+ manually: https://www.python.org/downloads/" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Auto-create venv if missing (ensures dependencies are available)
# ---------------------------------------------------------------------------
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
  echo "No .venv found. Creating virtual environment and installing dependencies..."
  "$PYTHON" -m venv "$PROJECT_ROOT/.venv"
  "$PROJECT_ROOT/.venv/bin/pip" install -q --upgrade pip
  "$PROJECT_ROOT/.venv/bin/pip" install -q -r "$PROJECT_ROOT/requirements.txt"
  echo "Virtual environment created."
else
  # Ensure dependencies are up-to-date (fast no-op if nothing changed)
  "$PROJECT_ROOT/.venv/bin/pip" install -q -r "$PROJECT_ROOT/requirements.txt" 2>/dev/null || true
fi

# Re-resolve to venv python after potential creation
if [ -x "$PROJECT_ROOT/.venv/bin/python3" ]; then
  PYTHON="$PROJECT_ROOT/.venv/bin/python3"
elif [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
  PYTHON="$PROJECT_ROOT/.venv/bin/python"
fi

# ---------------------------------------------------------------------------
# Port declaration (exported so child processes can discover services)
# Each port honours an existing environment value, so a port that is already
# taken on this machine can be moved without editing this script:
#   WEB_FRONTEND_PORT=8088 ./start.sh
# ---------------------------------------------------------------------------
# agent
export AGENT_PORT="${AGENT_PORT:-8080}"
# merchant
export MERCHANT_PORT="${MERCHANT_PORT:-8081}"
# credential provider
export CREDENTIALS_PROVIDER_PORT="${CREDENTIALS_PROVIDER_PORT:-8082}"
# alipayplus network
export ALIPAYPLUS_NETWORK_PORT="${ALIPAYPLUS_NETWORK_PORT:-8083}"
# alipayplus mandate
export ALIPAYPLUS_MANDATE_PORT="${ALIPAYPLUS_MANDATE_PORT:-8084}"
# acquirer
export ACQUIRER_PORT="${ACQUIRER_PORT:-8085}"
# mpp
export MPP_PORT="${MPP_PORT:-8086}"
# web frontend
export WEB_FRONTEND_PORT="${WEB_FRONTEND_PORT:-8088}"
# IDV deferred mode: MPP waits for external /completeIdv trigger (web interactive)
# Set to false for auto-complete mode (MPP auto-completes IDV after 0.5s)
# true is the designed interactive mode: CP returns PENDING_IDV immediately and
# the user confirms on the IDV card (requires the agent's PENDING_IDV branch).
export IDV_DEFERRED=true


# Environment variable initialization
if [ -f "$PROJECT_ROOT/.env" ]; then
  set -a
  source "$PROJECT_ROOT/.env"
  set +a
fi

# ---------------------------------------------------------------------------
# Temporary database declaration
# ---------------------------------------------------------------------------
export TEMP_DB_DIR="$SCRIPT_DIR/.temp-db"

rm -rf "$TEMP_DB_DIR" "$LOG_DIR"
mkdir -p "$TEMP_DB_DIR"
mkdir -p "$LOG_DIR"

export TOKEN_STORE_PATH="$TEMP_DB_DIR/token_store.db"
export MERCHANT_STORE_PATH="$TEMP_DB_DIR/merchant.db"
export SECRET_KEY_FILE="$TEMP_DB_DIR/keys.json"

# Startup log: captures verbose startup noise; summary block still goes to terminal
STARTUP_LOG="$LOG_DIR/startup.log"
: > "$STARTUP_LOG"

# Process management
pids=()

cleanup() {
  echo ""
  echo "Shutting down..."
  if [[ ${#pids[@]} -gt 0 ]]; then
    kill -TERM "${pids[@]}" 2>/dev/null || true
    sleep 1
    kill -KILL "${pids[@]}" 2>/dev/null || true
    wait "${pids[@]}" 2>/dev/null || true
  fi
  echo "Done."
}

trap cleanup EXIT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# kill_port PORT
#   Kills any process listening on the given port.
kill_port() {
  local port="$1"
  local pid
  pid=$(lsof -ti tcp:"${port}" || true)
  if [ -n "$pid" ]; then
    echo "Killing process $pid on port $port" >> "$STARTUP_LOG"
    kill -9 $pid 2>/dev/null || true
  fi
}


# port_in_use PORT
#   True when anything is listening on PORT. Uses netstat rather than lsof:
#   an unprivileged lsof cannot see sockets owned by other users, so a port
#   held by a system/company-managed service looks free to kill_port.
port_in_use() {
  netstat -an 2>/dev/null | grep -qE "[.:]$1[[:space:]]+.*LISTEN"
}


# require_free_port PORT NAME ENV_VAR
#   Frees PORT of our own leftovers, then insists it is really free. Failing
#   here (before anything starts) beats a service silently landing on another
#   port and every later health check timing out.
require_free_port() {
  local port="$1" name="$2" var="$3" i
  kill_port "$port"
  for (( i = 0; i < 10; i++ )); do
    port_in_use "$port" || return 0
    sleep 0.3
  done
  echo "ERROR: port $port ($name) is in use by a process this script cannot stop." >&2
  echo "       'lsof -ti tcp:$port' found nothing, so it belongs to another user" >&2
  echo "       (inspect with: sudo lsof -nP -iTCP:$port -sTCP:LISTEN)." >&2
  echo "       Run on a free port instead, e.g.:  $var=$(( port + 1000 )) ./start.sh" >&2
  exit 1
}


# start_service NAME DIR COMMAND PORT
#   Launches COMMAND inside DIR in the background, redirects output to a log
#   file named after NAME, and records the PID for cleanup.
#   ``exec`` replaces the subshell with the server itself, so the recorded PID
#   is the process actually holding the port — without it cleanup would only
#   reap the subshell and leave an orphaned server listening.
start_service() {
  local name="$1" dir="$2" cmd="$3" port="$4"
  echo "Starting ${name} (port ${port})..." >> "$STARTUP_LOG"
  echo "Starting ${name} (port ${port})..."
  # Support both absolute and relative paths
  if [[ "$dir" = /* ]]; then
    (cd "$dir" && eval "exec $cmd") >"$LOG_DIR/${name}.log" 2>&1 &
  else
    (cd "$SCRIPT_DIR/$dir" && eval "exec $cmd") >"$LOG_DIR/${name}.log" 2>&1 &
  fi
  pids+=("$!")
}

# tail_service NAME
#   Starts tailing the service log file to the terminal.
#   Uses -n 0 to skip existing content; only new lines (post-startup HTTP interactions) appear.
tail_service() {
  local name="$1"
  while IFS= read -r line; do
    if [ "${#line}" -gt 200 ]; then
      echo "[$name] ${line:0:200}..."
    else
      echo "[$name] $line"
    fi
  done < <(tail -f -n 0 "$LOG_DIR/${name}.log" 2>/dev/null) &
  pids+=("$!")
}

# wait_for_url URL [TIMEOUT_SECONDS]
#   Polls URL every 0.5s until it returns HTTP 200 or the timeout expires.
wait_for_url() {
  local url="$1"
  local timeout="${2:-15}"
  local attempts=$(( timeout * 2 ))

  for (( i = 1; i <= attempts; i++ )); do
    if curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null | grep -q 200; then
      return 0
    fi
    sleep 0.5
  done

  echo "ERROR: Timed out after ${timeout}s waiting for $url" >&2
  exit 1
}

# ---------------------------------------------------------------------------
# Launch services
# ---------------------------------------------------------------------------

# Force Python to flush stdout/stderr immediately (needed for tail -f on log files)
export PYTHONUNBUFFERED=1

echo "Using Python: $PYTHON" >> "$STARTUP_LOG"


# declare human present flow
export FLOW=human_present

# Pre-flight: reclaim our own leftovers and refuse to start if any port is
# still occupied — a service that silently lands elsewhere only surfaces later
# as a health-check timeout that tears the whole stack down.
require_free_port "$AGENT_PORT"                 "shopping-agent"      AGENT_PORT
require_free_port "$MERCHANT_PORT"              "merchant"            MERCHANT_PORT
require_free_port "$CREDENTIALS_PROVIDER_PORT"  "credential-provider" CREDENTIALS_PROVIDER_PORT
require_free_port "$ALIPAYPLUS_NETWORK_PORT"    "alipayplus-network"  ALIPAYPLUS_NETWORK_PORT
require_free_port "$ALIPAYPLUS_MANDATE_PORT"    "alipayplus-mandate"  ALIPAYPLUS_MANDATE_PORT
require_free_port "$ACQUIRER_PORT"              "acquirer"            ACQUIRER_PORT
require_free_port "$MPP_PORT"                   "mpp"                 MPP_PORT
require_free_port "$WEB_FRONTEND_PORT"          "web-frontend"        WEB_FRONTEND_PORT

# Shopping Agent (agent entry — provides /task endpoints for the web frontend)
start_service "shopping-agent" "../../../../samples/python/shopping_agent" \
  "$PYTHON server.py --port $AGENT_PORT" $AGENT_PORT
wait_for_url "http://localhost:$AGENT_PORT/health"

# Merchant
start_service "merchant" "$PROJECT_ROOT/samples/python/merchant" \
  "$PYTHON trigger_server.py $MERCHANT_PORT" $MERCHANT_PORT
wait_for_url "http://localhost:$MERCHANT_PORT/health"

# Credential Provider
start_service "credential-provider" "$PROJECT_ROOT/samples/python/credential_provider" \
  "$PYTHON trigger_server.py $CREDENTIALS_PROVIDER_PORT" $CREDENTIALS_PROVIDER_PORT
wait_for_url "http://localhost:$CREDENTIALS_PROVIDER_PORT/health"

# AlipayPlus Network
start_service "alipayplus-network" "$PROJECT_ROOT/samples/python/alipayplus" \
  "$PYTHON trigger_server.py network $ALIPAYPLUS_NETWORK_PORT" $ALIPAYPLUS_NETWORK_PORT
wait_for_url "http://localhost:$ALIPAYPLUS_NETWORK_PORT/docs"

# AlipayPlus Mandate
start_service "alipayplus-mandate" "$PROJECT_ROOT/samples/python/alipayplus" \
  "$PYTHON trigger_server.py mandate $ALIPAYPLUS_MANDATE_PORT" $ALIPAYPLUS_MANDATE_PORT
wait_for_url "http://localhost:$ALIPAYPLUS_MANDATE_PORT/docs"

# Acquirer
start_service "acquirer" "$PROJECT_ROOT/samples/python/acquirer" \
  "$PYTHON trigger_server.py $ACQUIRER_PORT" $ACQUIRER_PORT
wait_for_url "http://localhost:$ACQUIRER_PORT/health"

# MPP
start_service "mpp" "$PROJECT_ROOT/samples/python/mpp" \
  "$PYTHON trigger_server.py $MPP_PORT" $MPP_PORT
wait_for_url "http://localhost:$MPP_PORT/mpp/health"

# ---------------------------------------------------------------------------
# Web Client (frontend)
# ---------------------------------------------------------------------------
WEB_CLIENT_DIR="$PROJECT_ROOT/samples/python/shopping_agent/web_frontend"

# Auto-install npm dependencies if vite is missing
if [ ! -d "$WEB_CLIENT_DIR/node_modules/vite" ]; then
  echo "Installing web-frontend npm dependencies..." >> "$STARTUP_LOG"
  (cd "$WEB_CLIENT_DIR" && npm install) >> "$STARTUP_LOG" 2>&1
fi

# ``exec`` the vite binary directly instead of going through npx: the recorded
# PID is then the dev server itself, so cleanup really stops it (an npx wrapper
# would leave the node grandchild listening after Ctrl+C). --strictPort makes
# vite fail loudly rather than drift to the next free port behind our back.
echo "Starting web-frontend (port $WEB_FRONTEND_PORT)..." >> "$STARTUP_LOG"
(cd "$WEB_CLIENT_DIR" && exec ./node_modules/.bin/vite --port $WEB_FRONTEND_PORT --strictPort) \
  >"$LOG_DIR/web-frontend.log" 2>&1 &
pids+=("$!")

# Wait for frontend to be ready
wait_for_url "http://localhost:$WEB_FRONTEND_PORT" 20

echo ""
echo "All services started successfully. (FLOW=human_present → IMMEDIATE mode)"
echo "  Shopping Agent      : http://localhost:$AGENT_PORT"
echo "  Merchant            : http://localhost:$MERCHANT_PORT"
echo "  AlipayPlus Network  : http://localhost:$ALIPAYPLUS_NETWORK_PORT"
echo "  Credential Provider : http://localhost:$CREDENTIALS_PROVIDER_PORT"
echo "  AlipayPlus Mandate  : http://localhost:$ALIPAYPLUS_MANDATE_PORT"
echo "  Acquirer            : http://localhost:$ACQUIRER_PORT"
echo "  MPP                 : http://localhost:$MPP_PORT"
echo "  Web Frontend        : http://localhost:$WEB_FRONTEND_PORT"
echo ""
echo "Open http://localhost:$WEB_FRONTEND_PORT in your browser to interact with the agent."
echo "Press Ctrl+C to stop."

# Start tailing service logs — only new lines (HTTP interactions) will appear
tail_service "alipayplus-network"
tail_service "alipayplus-mandate"
tail_service "credential-provider"
tail_service "merchant"
tail_service "acquirer"
tail_service "mpp"
tail_service "shopping-agent"
tail_service "web-frontend"

wait
