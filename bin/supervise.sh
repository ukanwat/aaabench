#!/usr/bin/env bash
# Keep one campaign running, session after session, indefinitely.
#
#   ./bin/supervise.sh                      # new campaign
#   CAMPAIGN=runs/20260815-0100 ./bin/supervise.sh    # continue an existing one
#   touch /tmp/aaabench-pause               # finish the current session, then stop
#   ./bin/results.sh --list
#
# One workspace, many sessions. Each session starts cold with no memory of the last, and the only
# continuity is what the agent wrote down — which is the thing being measured, so the supervisor
# must not help it along. It starts sessions and gets out of the way.
#
# What it does do: never run two at once, never spin. If sessions start failing fast, the delay
# grows, because a tight relaunch loop against a broken environment burns a night's budget and
# produces nothing.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CAMPAIGN="${CAMPAIGN:-$ROOT/runs/$(date +%Y%m%d-%H%M%S)}"
PAUSE="${PAUSE:-/tmp/aaabench-pause}"
LOCK="/tmp/aaabench-supervisor.lock"
MIN_OK_MIN="${MIN_OK_MIN:-10}"     # a session shorter than this counts as a failure
BACKOFF_START=30
BACKOFF_MAX=1800

if ! mkdir "$LOCK" 2>/dev/null; then
  other=$(cat "$LOCK/pid" 2>/dev/null || echo "")
  if [[ -n "$other" ]] && kill -0 "$other" 2>/dev/null; then
    echo "a supervisor is already running (pid $other)"; exit 1
  fi
  rm -rf "$LOCK"; mkdir "$LOCK"
fi
echo $$ > "$LOCK/pid"
trap 'rm -rf "$LOCK"; echo "supervisor stopped"' EXIT

mkdir -p "$CAMPAIGN"
echo "campaign:  $CAMPAIGN"
echo "workspace: $CAMPAIGN/workspace"
echo "pause:     touch $PAUSE"
echo

backoff=$BACKOFF_START
n=0
while :; do
  if [[ -f "$PAUSE" ]]; then
    echo "$(date +%H:%M:%S)  paused — remove $PAUSE to resume"
    sleep 60
    continue
  fi

  n=$((n + 1))
  started=$(date +%s)
  echo "=== session $n starting $(date +%H:%M:%S) ==="
  CAMPAIGN="$CAMPAIGN" ./bin/run-agent.sh
  status=$?
  mins=$((($(date +%s) - started) / 60))
  echo "=== session $n ended after ${mins}m (exit $status) ==="

  if (( mins >= MIN_OK_MIN )); then
    backoff=$BACKOFF_START               # a real session ran; reset
    sleep 20
  else
    echo "    short session — backing off ${backoff}s"
    sleep "$backoff"
    backoff=$(( backoff * 2 > BACKOFF_MAX ? BACKOFF_MAX : backoff * 2 ))
  fi
done
