#!/usr/bin/env python3
"""SubagentStop hook: log every subagent completion.

Fires after a subagent finishes (success, error, or timeout). More reliable
than PreToolUse on the Agent tool — empirically that hook misses custom
project-defined subagent types, while SubagentStop fires for both built-in
(Explore, Plan, general-purpose) and custom types (.claude/agents/*.md).

Schema (from Claude Code docs, verified):
  {
    "session_id": "...",
    "transcript_path": "...",
    "cwd": "...",
    "hook_event_name": "SubagentStop",
    "agent_id": "...",
    "agent_type": "Explore" | "<custom>",
    "stop_reason": "completed" | "error" | ...
  }

Always exits 0 — never block agent execution.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        agent_type = data.get('agent_type')
        if not agent_type:
            return 0

        log_dir = Path.home() / '.claude' / 'local-telemetry' / 'tools'
        log_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        log_file = log_dir / f'{now:%Y-%m}.jsonl'

        entry = {
            'ts': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'tool': 'Agent',
            'event': 'SubagentStop',
            'skill': None,
            'subagent': agent_type,
            'slash_command': None,
            'description': None,
            'stop_reason': data.get('stop_reason'),
            'agent_id': data.get('agent_id'),
            'cwd': os.getcwd(),
            'session_id': data.get('session_id'),
        }

        with log_file.open('a') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
