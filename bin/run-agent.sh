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
EFFORT="${EFFORT:-xhigh}"                # low|medium|high|xhigh|max — a confound if it differs between arms
# Deliberately NO --fallback-model. Falling back to another model when this one is busy would
# silently change the subject under test, and the run would look successful. Better to stall.
PORT="${PORT:-8080}"
MAX_NUDGES="${MAX_NUDGES:-12}"           # long-horizon: an early stop is normal, not terminal
SESSION_MIN="${SESSION_MIN:-180}"        # a session is expected to run this long
PY="${PY:-$HOME/imagegen/bin/python}"    # the interpreter with playwright, for the sensors
LOCK="/tmp/aaabench-web.lock"
# A campaign is a world worked on across many sessions; a session is one agent invocation.
# The workspace belongs to the campaign, not the session — continuity across sessions IS the
# thesis, and a fresh world each time would measure something else entirely.
CAMPAIGN="${CAMPAIGN:-$ROOT/runs/$(date +%Y%m%d-%H%M%S)}"
WORKSPACE="${WORKSPACE:-$CAMPAIGN/workspace}"
LOG_DIR="${LOG_DIR:-$CAMPAIGN/sessions/$(date +%Y%m%d-%H%M%S)}"

# Single-instance lock. mkdir is atomic everywhere; `flock` is not — it does not exist on
# macOS at all, and a lock that silently fails is worse than no lock, because two runners
# fighting over the port produce a page that never loads and reads to the agent as its bug.
if ! mkdir "$LOCK" 2>/dev/null; then
  OTHER=$(cat "$LOCK/pid" 2>/dev/null || echo "")
  if [[ -n "$OTHER" ]] && kill -0 "$OTHER" 2>/dev/null; then
    echo "another run is live (pid $OTHER) — refusing to start a second one"; exit 1
  fi
  echo "clearing a stale lock from pid ${OTHER:-unknown}"
  rm -rf "$LOCK"; mkdir "$LOCK" || { echo "cannot take $LOCK"; exit 1; }
fi
echo $$ > "$LOCK/pid"
trap 'rm -rf "$LOCK"' EXIT

# Credentials live OUTSIDE the repo — this repo is public and a committed token is a bad day.
# ~/.aaabench.env is chmod 600 and holds `export SKETCHFAB_API_TOKEN=…` style lines.
if [[ -f "$HOME/.aaabench.env" ]]; then
  set -a; source "$HOME/.aaabench.env"; set +a
  echo "keys:     $(grep -c '^export' "$HOME/.aaabench.env") loaded from ~/.aaabench.env"
else
  echo "keys:     none — ~/.aaabench.env not present; login-walled sources stay closed"
fi

# Mixamo's bearer is an Adobe IMS token with a 24h life. A run that starts on a dead one
# loses its best animation source silently — the API just 401s and the agent concludes the
# source does not work. Check the expiry rather than discovering it mid-session.
if [[ -n "${MIXAMO_BEARER:-}" ]]; then
  MIX_LEFT=$(python3 - <<'PYEOF'
import base64, json, os, time
try:
    p = os.environ["MIXAMO_BEARER"].split(".")[1]; p += "=" * (-len(p) % 4)
    d = json.loads(base64.urlsafe_b64decode(p))
    print(round(((int(d["created_at"]) + int(d["expires_in"])) / 1000 - time.time()) / 3600, 1))
except Exception:
    print("?")
PYEOF
)
  if [[ "$MIX_LEFT" == "?" ]] || (( $(echo "$MIX_LEFT <= 1" | bc -l) )); then
    echo "mixamo:   BEARER EXPIRED — ask the operator for a fresh one before relying on it."
    echo "          They mint it from their own browser: devtools on mixamo.com,"
    echo "          copy(localStorage.access_token), then update ~/.aaabench.env"
  else
    echo "mixamo:   bearer valid ${MIX_LEFT}h"
  fi
fi

# Each run gets its own workspace, and that workspace is its own git repository. Two reasons:
# a later run must never inherit an earlier one's world, and the agent's output must never be
# able to land in the benchmark repo (an operator's `git add -A` already swept it in once).
mkdir -p "$LOG_DIR" "$WORKSPACE"
if [[ ! -d "$WORKSPACE/.git" ]]; then
  git -C "$WORKSPACE" init -q
  git -C "$WORKSPACE" symbolic-ref HEAD refs/heads/main 2>/dev/null
  printf 'node_modules/\ndist/\n.DS_Store\n' > "$WORKSPACE/.gitignore"
  git -C "$WORKSPACE" add -A
  git -C "$WORKSPACE" -c user.name="AAABench agent" -c user.email="agent@aaabench.local" \
      commit -q -m "Empty room" 2>/dev/null
fi
echo "campaign: $CAMPAIGN"
echo "session:  $LOG_DIR"
echo "agent:    $AGENT   model: $MODEL   effort: $EFFORT"
echo "budget:   ${SESSION_MIN}min, up to $MAX_NUDGES resumes"
echo "sensors:  $PY tools/shot.py    server: :$PORT"

# --- server -----------------------------------------------------------------
if lsof -ti :"$PORT" >/dev/null 2>&1; then
  echo "port $PORT is already held — a stale server reads to the agent as a broken page"
  lsof -ti :"$PORT" | xargs kill -9 2>/dev/null
  sleep 1
fi
python3 tools/serve.py --dir "$WORKSPACE" --port "$PORT" > "$LOG_DIR/serve.log" 2>&1 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null; rm -rf "$LOCK"' EXIT   # replaces the lock-only trap above
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
cat >> "$PROMPT_FILE" <<EOF


---

**Where you are.** Your working directory is \`$WORKSPACE\` — a fresh git repository that belongs
to you. Everything you build, every document, every tool you write and every asset you fetch lives
there and nowhere else. Commit in it freely; nothing outside it is yours to change.

The harness is a separate directory at \`$ROOT\`, and it is **read-only to you**. Where this brief
says \`docs/...\`, \`tools/...\` or \`.claude/skills/...\`, it means paths under \`$ROOT\` — so
\`$ROOT/docs/INDEX.md\`, \`$ROOT/tools/shot.py\`, \`$ROOT/tools/gen-image.py\`.

The page is served at http://127.0.0.1:$PORT from your working directory.
EOF

agent_run() {
  local prompt_path="$1" resume="$2"
  cd "$WORKSPACE" || return 1
  case "$AGENT" in
    claude)
      local common=(--model "$MODEL" --effort "$EFFORT" --dangerously-skip-permissions
                    --add-dir "$ROOT" --output-format stream-json --verbose)
      if [[ "$resume" == "1" ]]; then
        claude --continue "${common[@]}" -p "$(cat "$prompt_path")"
      else
        claude "${common[@]}" -p "$(cat "$prompt_path")"
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

  # What model did this session ACTUALLY run on? The stream-json init event says so, and a
  # previous run in this project was contaminated by an alias resolving to another generation.
  python3 - "$LOG_DIR/agent.log" "$LOG_DIR/models.txt" <<'PYEOF'
import json, sys
seen, rl = set(), 0
try:
    for line in open(sys.argv[1], errors="replace"):
        line = line.strip()
        if not line.startswith("{"): continue
        try: d = json.loads(line)
        except Exception: continue
        if d.get("type") == "system" and d.get("model"): seen.add(d["model"])
        if d.get("type") == "rate_limit_event": rl += 1
except FileNotFoundError:
    pass
open(sys.argv[2], "w").write("models: %s\nrate_limit_events: %d\n" % (sorted(seen) or ["unknown"], rl))
print("  models used:", sorted(seen) or "unknown", "| rate-limit events:", rl)
PYEOF

  cd "$ROOT"
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
    python3 tools/serve.py --dir "$WORKSPACE" --port "$PORT" >> "$LOG_DIR/serve.log" 2>&1 &
    SERVER_PID=$!
  fi
done

echo "logs: $LOG_DIR"
