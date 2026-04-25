#!/usr/bin/env python3
"""UserPromptSubmit hook: detect slash-command prompts and log them.

Slash commands like `/lnb-review-pr 6515` are expanded inline by Claude Code
and never go through the Skill tool, so the PreToolUse hook can't see them.
This hook reads the raw prompt and logs any line starting with `/<name>`.

Appends to the same ~/.claude/local-telemetry/tools/YYYY-MM.jsonl file.
Always exits 0 — never block prompt submission.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


SLASH_RE = re.compile(r'^\s*/([A-Za-z][\w:.-]*)')


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        prompt = data.get('prompt') or ''
        match = SLASH_RE.match(prompt)
        if match is None:
            return 0  # not a slash command, nothing to log

        log_dir = Path.home() / '.claude' / 'local-telemetry' / 'tools'
        log_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        log_file = log_dir / f'{now:%Y-%m}.jsonl'

        entry = {
            'ts': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'cwd': os.getcwd(),
            'session_id': data.get('session_id'),
            'tool': 'SlashCommand',
            'skill': None,
            'subagent': None,
            'slash_command': match.group(1),
            'description': None,
        }

        with log_file.open('a') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
