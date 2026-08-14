#!/usr/bin/env bash
# One session: start the server, hand over the demand, keep it going if it stops early.
#
#   ./bin/run-agent.sh
#   AGENT=codex ./bin/run-agent.sh
#   MODEL=claude-opus-5 MAX_NUDGES=6 ./bin/run-agent.sh
#   NOTE=notes/restart.md ./bin/run-agent.sh      # prepended to the demand on a restart
#
# The harness rule this script exists to respect: it provides conditions and the demand, and
# nothing else. It never tells the agent what is wrong with its build. See HARNESS-RULES.md.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

AGENT="${AGENT:-claude}"
MODEL="${MODEL:-claude-opus-5}"          # pin the full id — bare aliases have resolved to another generation
PORT="${PORT:-8080}"
MAX_NUDGES="${MAX_NUDGES:-4}"
SESSION_MIN="${SESSION_MIN:-180}"        # a session is expected to run this long
PY="${PY:-$HOME/imagegen/bin/python}"    # the interpreter with playwright, for the sensors
LOCK="/tmp/aaabench-web.lock"
LOG_DIR="$ROOT/runs/$(date +%Y%m%d-%H%M%S)"

exec 9>"$LOCK"
flock -n 9 || { echo "another run holds $LOCK — refusing to start a second one"; exit 1; }

mkdir -p "$LOG_DIR" workspace
echo "run:      $LOG_DIR"
echo "agent:    $AGENT   model: $MODEL"
echo "sensors:  $PY tools/shot.py    server: :$PORT"

# --- server -----------------------------------------------------------------
if lsof -ti :"$PORT" >/dev/null 2>&1; then
  echo "port $PORT is already held — a stale server reads to the agent as a broken page"
  lsof -ti :"$PORT" | xargs kill -9 2>/dev/null
  sleep 1
fi
python3 tools/serve.py --dir workspace --port "$PORT" > "$LOG_DIR/serve.log" 2>&1 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null' EXIT
sleep 1
kill -0 $SERVER_PID 2>/dev/null || { echo "server failed to start — see $LOG_DIR/serve.log"; exit 1; }

# --- the GPU check, before the agent wastes a session on software frames -----
"$PY" tools/shot.py --gpu-info > "$LOG_DIR/gpu.json" 2>&1
if grep -q '"webgpu": false' "$LOG_DIR/gpu.json" || grep -qi swiftshader "$LOG_DIR/gpu.json"; then
  echo "WARNING: the sensor is not getting the GPU. Every frame the agent looks at would be"
  echo "         software-rendered. Fix this before running — see docs/tech/feedback.md"
  cat "$LOG_DIR/gpu.json"
fi

# --- the demand -------------------------------------------------------------
PROMPT_FILE="$LOG_DIR/prompt.md"
: > "$PROMPT_FILE"
if [[ -n "${NOTE:-}" && -f "$NOTE" ]]; then
  cat "$NOTE" >> "$PROMPT_FILE"; printf '\n\n---\n\n' >> "$PROMPT_FILE"
  echo "note:     $NOTE  (logged as a contamination-log entry — check it carries no diagnosis)"
fi
cat PROMPT.md >> "$PROMPT_FILE"
printf '\n\nThe page is served at http://127.0.0.1:%s from ./workspace.\n' "$PORT" >> "$PROMPT_FILE"

agent_run() {
  local prompt_path="$1" resume="$2"
  case "$AGENT" in
    claude)
      if [[ "$resume" == "1" ]]; then
        claude --continue --model "$MODEL" --dangerously-skip-permissions -p "$(cat "$prompt_path")"
      else
        claude --model "$MODEL" --dangerously-skip-permissions -p "$(cat "$prompt_path")"
      fi ;;
    codex)  codex exec --full-auto "$(cat "$prompt_path")" ;;
    gemini) gemini --yolo -p "$(cat "$prompt_path")" ;;
    custom) eval "${AGENT_CMD:?set AGENT_CMD}" "$prompt_path" ;;
    *) echo "unknown AGENT=$AGENT — add a preset in agent_run()"; exit 1 ;;
  esac
}

# --- run, and resume rather than restart if it stops with time left ----------
START=$(date +%s)
NUDGE=0
RESUME=0
CONTINUE_MSG="$LOG_DIR/continue.md"
printf 'Prior work stands. Continue.\n' > "$CONTINUE_MSG"

while :; do
  echo "--- session start (nudge $NUDGE) $(date +%H:%M:%S) ---" | tee -a "$LOG_DIR/agent.log"
  if [[ "$RESUME" == "1" ]]; then
    agent_run "$CONTINUE_MSG" 1 2>&1 | tee -a "$LOG_DIR/agent.log"
  else
    agent_run "$PROMPT_FILE" 0 2>&1 | tee -a "$LOG_DIR/agent.log"
  fi

  ELAPSED=$(( ($(date +%s) - START) / 60 ))
  if (( ELAPSED >= SESSION_MIN )); then
    echo "session used its time (${ELAPSED}m) — done"; break
  fi
  NUDGE=$((NUDGE+1))
  if (( NUDGE > MAX_NUDGES )); then
    echo "stopped early ${MAX_NUDGES} times (${ELAPSED}m used) — giving up"; break
  fi
  echo "stopped after ${ELAPSED}m of ${SESSION_MIN} — resuming the same session so its plan survives"
  RESUME=1

  if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "server died — restarting it"
    python3 tools/serve.py --dir workspace --port "$PORT" >> "$LOG_DIR/serve.log" 2>&1 &
    SERVER_PID=$!
  fi
done

echo "logs: $LOG_DIR"
