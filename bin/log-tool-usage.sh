#!/usr/bin/env bash
# PreToolUse hook: appends one JSONL line per Skill/Task invocation to
# ~/.claude/local-telemetry/tools/YYYY-MM.jsonl
#
# Hook input arrives on stdin as JSON. We extract the fields we care about
# and add a UTC timestamp + cwd so reports can split global vs project usage.
# We always exit 0 so a logging failure never blocks a tool call.

set -u

LOG_DIR="$HOME/.claude/local-telemetry/tools"
mkdir -p "$LOG_DIR" 2>/dev/null || exit 0
LOG_FILE="$LOG_DIR/$(date -u +%Y-%m).jsonl"

if ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

jq -c \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg cwd "$PWD" \
  '{
    ts: $ts,
    cwd: $cwd,
    session_id: .session_id,
    tool: .tool_name,
    skill: .tool_input.skill,
    subagent: .tool_input.subagent_type,
    description: .tool_input.description
  }' >> "$LOG_FILE" 2>/dev/null || true

exit 0
