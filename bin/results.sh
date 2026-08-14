#!/usr/bin/env bash
# What happened in a run.
#
#   ./bin/results.sh              # the most recent run
#   ./bin/results.sh 20260814-222943
#   ./bin/results.sh --list
#   ./bin/results.sh --shot       # also capture the page as it stands now
#
# Reads the run's stream-json log rather than summarising from memory, so everything here is
# what the session actually reported.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="${PY:-$HOME/imagegen/bin/python}"

[[ "${1:-}" == "--list" ]] && { ls -1 runs/ 2>/dev/null || echo "no runs yet"; exit 0; }

SHOT=0
[[ "${1:-}" == "--shot" ]] && { SHOT=1; shift; }
RUN="${1:-$(ls -1 runs/ 2>/dev/null | tail -1)}"
[[ -z "$RUN" || ! -d "runs/$RUN" ]] && { echo "no such run: ${RUN:-<none>}"; exit 1; }
D="runs/$RUN"

echo "run:       $RUN"
pgrep -f "run-agent.sh" >/dev/null && echo "state:     RUNNING" || echo "state:     finished"

python3 - "$D/agent.log" <<'PYEOF'
import json, sys, collections
path = sys.argv[1]
tools = collections.Counter(); models = set(); rl = 0
texts = []; turns = 0; cost = 0.0; first = last = None
try:
    for line in open(path, errors="replace"):
        line = line.strip()
        if not line.startswith("{"): continue
        try: d = json.loads(line)
        except Exception: continue
        t = d.get("type")
        if t == "system" and d.get("model"): models.add(d["model"])
        if t == "rate_limit_event": rl += 1
        if t == "result":
            cost += d.get("total_cost_usd") or 0
            turns += d.get("num_turns") or 0
        if t == "assistant":
            for c in (d.get("message", {}).get("content") or []):
                if c.get("type") == "tool_use": tools[c["name"]] += 1
                if c.get("type") == "text" and c.get("text", "").strip():
                    texts.append(c["text"].strip())
                    if first is None: first = c["text"].strip()
                    last = c["text"].strip()
except FileNotFoundError:
    print("  (no agent.log)"); raise SystemExit

print("model:     %s%s" % (", ".join(sorted(models)) or "unknown",
                           "   <-- MORE THAN ONE MODEL, the run is contaminated" if len(models) > 1 else ""))
print("turns:     %d   tool calls: %d   rate-limit events: %d" % (turns, sum(tools.values()), rl))
if cost: print("cost:      $%.2f" % cost)
print("tools:     " + ", ".join(f"{k} {v}" for k, v in tools.most_common(8)))
if last:
    print("\nlast said: " + " ".join(last.split())[:300])
PYEOF

echo
echo "workspace: $(git -C workspace rev-list --count HEAD 2>/dev/null || echo 0) commit(s), $(git -C workspace ls-files 2>/dev/null | wc -l | tr -d ' ') tracked files"
git -C workspace log --oneline 2>/dev/null | head -5 | sed 's/^/  /'
for f in PROGRESS.md MAP_PLAN.md STORY_BIBLE.md ASSETS.md WORLD_INVENTORY.md; do
  [[ -f "workspace/$f" ]] && printf "  %-18s %s lines\n" "$f" "$(wc -l < "workspace/$f" | tr -d ' ')"
done

echo
if curl -s -o /dev/null -m 5 -w "" http://127.0.0.1:8080/ 2>/dev/null; then
  echo "page:      http://127.0.0.1:8080  (open it)"
else
  echo "page:      not served — run: python3 tools/serve.py"
fi

if [[ "$SHOT" == "1" ]]; then
  echo
  "$PY" tools/shot.py http://127.0.0.1:8080 -o "$D/latest.png" --wait 4000 --frames 60 2>&1 | sed 's/^/  /'
  echo "  -> $D/latest.png"
fi
