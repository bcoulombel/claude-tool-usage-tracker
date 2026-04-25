#!/usr/bin/env bash
# Print a markdown report of Skill/Agent usage for a given period.
# Usage: report.sh [all|30d|7d]   (default: 30d)

set -euo pipefail

PERIOD="${1:-30d}"
LOG_DIR="$HOME/.claude/local-telemetry/tools"

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: \`jq\` is required but not installed." >&2
  echo "Install it with: brew install jq" >&2
  exit 1
fi

if [[ ! -d "$LOG_DIR" ]] || ! ls "$LOG_DIR"/*.jsonl >/dev/null 2>&1; then
  echo "No usage logs found in $LOG_DIR yet."
  echo "The PreToolUse hook will populate logs on the next Skill or Task invocation."
  exit 0
fi

case "$PERIOD" in
  all)
    CUTOFF=""
    LABEL="all-time"
    ;;
  7d)
    CUTOFF=$(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)
    LABEL="last 7 days"
    ;;
  30d)
    CUTOFF=$(date -u -v-30d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%SZ)
    LABEL="last 30 days"
    ;;
  *)
    echo "Unknown period: $PERIOD (expected: all, 7d, 30d)" >&2
    exit 1
    ;;
esac

echo "# Tool usage — $LABEL"
echo
echo "| Name | Kind | Count |"
echo "|------|------|------:|"

jq -rs --arg cutoff "$CUTOFF" '
  map(select($cutoff == "" or .ts >= $cutoff))
  | group_by(.skill // .subagent // .tool)
  | map({
      name: (.[0].skill // .[0].subagent // .[0].tool),
      kind: (if .[0].skill then "skill"
             elif .[0].subagent then "agent"
             else "other" end),
      count: length
    })
  | sort_by(-.count)
  | .[]
  | "| \(.name) | \(.kind) | \(.count) |"
' "$LOG_DIR"/*.jsonl

TOTAL=$(jq -rs --arg cutoff "$CUTOFF" '
  map(select($cutoff == "" or .ts >= $cutoff)) | length
' "$LOG_DIR"/*.jsonl)

echo
echo "_Total invocations: ${TOTAL} — source: \`$LOG_DIR\`_"
