#!/usr/bin/env python3
"""Aggregate ~/.claude/local-telemetry/tools/*.jsonl and print a markdown report.

Usage: report.py [all|30d|7d]   (default: 30d)
"""
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


PERIODS = {
    'all': (None, 'all-time'),
    '7d': (timedelta(days=7), 'last 7 days'),
    '30d': (timedelta(days=30), 'last 30 days'),
}


def main(argv):
    period = argv[1] if len(argv) > 1 else '30d'
    if period not in PERIODS:
        print(f'Unknown period: {period} (expected: all, 7d, 30d)', file=sys.stderr)
        return 1
    delta, label = PERIODS[period]

    log_dir = Path.home() / '.claude' / 'local-telemetry' / 'tools'
    files = sorted(log_dir.glob('*.jsonl')) if log_dir.is_dir() else []
    if not files:
        print(f'No usage logs found in {log_dir} yet.')
        print('The PreToolUse hook will populate logs on the next Skill or Task invocation.')
        return 0

    cutoff = None
    if delta is not None:
        cutoff = (datetime.now(timezone.utc) - delta).strftime('%Y-%m-%dT%H:%M:%SZ')

    counts = Counter()
    total = 0
    for path in files:
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if cutoff is not None and (entry.get('ts') or '') < cutoff:
                    continue
                if entry.get('skill'):
                    name, kind = entry['skill'], 'skill'
                elif entry.get('subagent'):
                    name, kind = entry['subagent'], 'agent'
                else:
                    name, kind = entry.get('tool') or 'unknown', 'other'
                counts[(name, kind)] += 1
                total += 1

    print(f'# Tool usage — {label}')
    print()
    print('| Name | Kind | Count |')
    print('|------|------|------:|')
    for (name, kind), count in counts.most_common():
        print(f'| {name} | {kind} | {count} |')
    print()
    print(f'_Total invocations: {total} — source: `{log_dir}`_')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
