#!/usr/bin/env python3
"""PreToolUse hook: append one JSONL line per Skill/Task tool call.

Reads hook input from stdin, extracts the fields we care about, adds a UTC
timestamp and cwd, and appends to ~/.claude/local-telemetry/tools/YYYY-MM.jsonl.

Always exits 0 — a logging failure must never block a tool call.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    try:
        log_dir = Path.home() / '.claude' / 'local-telemetry' / 'tools'
        log_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        log_file = log_dir / f'{now:%Y-%m}.jsonl'

        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        tool_input = data.get('tool_input') or {}

        entry = {
            'ts': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'tool': data.get('tool_name'),
            'event': 'PreToolUse',
            'skill': tool_input.get('skill'),
            'subagent': tool_input.get('subagent_type'),
            'description': tool_input.get('description'),
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
