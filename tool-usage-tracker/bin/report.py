#!/usr/bin/env python3
"""Aggregate ~/.claude/local-telemetry/tools/*.jsonl and print a markdown report.

Usage: report.py [period] [--unused]
  period:    'all' or <N>[h|d|w|m]   (default: 30d)
  --unused:  also print the unused-tools table (off by default)

  Examples:
    report.py 7d                used-tools table only
    report.py 7d --unused       used + unused tables
    report.py all --unused      everything ever, plus what's never been touched

The unused-tools table is opt-in because it's long. Descriptions in that
table are truncated to a one-liner (first sentence, capped at 100 chars).

Discovery roots for unused tools (option B from the spec):
  - ~/.claude/{skills,agents,commands}/
  - ~/.claude/plugins/cache/*/*/*/{skills,agents,commands}/
  - <cwd>/.claude/{skills,agents,commands}/
"""
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


TYPE_ORDER = ['agent', 'skill', 'slash-cmd']
PERIOD_RE = re.compile(r'^(\d+)([hdwm])$')
UNIT_LABEL = {'h': 'hour', 'd': 'day', 'w': 'week', 'm': 'month'}
SKIP_DIRS = {'.bak', '.agents', 'node_modules', '__pycache__'}


# -- Period parsing ----------------------------------------------------------

def parse_period(period):
    """Return (timedelta_or_None, human_label) or (False, error_message)."""
    if period == 'all':
        return None, 'all-time'
    match = PERIOD_RE.match(period)
    if match is None:
        return False, (
            f'Unknown period: {period} '
            '(expected: all, or <N>[h|d|w|m] e.g. 1d, 7d, 30d, 2w, 3m)'
        )
    n, unit = int(match.group(1)), match.group(2)
    if unit == 'h':
        delta = timedelta(hours=n)
    elif unit == 'd':
        delta = timedelta(days=n)
    elif unit == 'w':
        delta = timedelta(weeks=n)
    else:
        delta = timedelta(days=30 * n)
    plural = 's' if n != 1 else ''
    return delta, f'last {n} {UNIT_LABEL[unit]}{plural}'


# -- Log aggregation ---------------------------------------------------------

def aggregate_logs(cutoff_iso):
    log_dir = Path.home() / '.claude' / 'local-telemetry' / 'tools'
    files = sorted(log_dir.glob('*.jsonl')) if log_dir.is_dir() else []
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
                if cutoff_iso is not None and (entry.get('ts') or '') < cutoff_iso:
                    continue
                if entry.get('slash_command'):
                    name, kind = entry['slash_command'], 'slash-cmd'
                elif entry.get('skill'):
                    name, kind = entry['skill'], 'skill'
                elif entry.get('subagent'):
                    name, kind = entry['subagent'], 'agent'
                else:
                    continue
                counts[(kind, name)] += 1
                total += 1
    return counts, total, log_dir, bool(files)


# -- Frontmatter parsing (no PyYAML dependency) ------------------------------

FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---', re.DOTALL)
KEY_RE = re.compile(r'^([A-Za-z_][\w\-]*)\s*:\s*(.*)$')


def parse_frontmatter(path):
    try:
        text = path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return {}
    match = FRONTMATTER_RE.match(text)
    if match is None:
        return {}
    return _parse_yaml_subset(match.group(1))


def _parse_yaml_subset(body):
    """Tolerant parser for top-level `key: value` and `key: |` block scalars."""
    out = {}
    lines = body.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == '' or line.lstrip().startswith('#'):
            i += 1
            continue
        if not re.match(r'^\S', line):
            i += 1
            continue
        match = KEY_RE.match(line)
        if match is None:
            i += 1
            continue
        key, rest = match.group(1), match.group(2).strip()
        if rest in ('|', '>', '|-', '>-', '|+', '>+'):
            chunks = []
            i += 1
            while i < len(lines):
                ln = lines[i]
                if ln.strip() and re.match(r'^\S', ln):
                    break
                if ln.strip():
                    chunks.append(ln.strip())
                i += 1
            out[key] = ' '.join(chunks).strip()
            continue
        if rest == '':
            chunks = []
            i += 1
            while i < len(lines):
                ln = lines[i]
                if ln.strip() and re.match(r'^\S', ln):
                    break
                if ln.strip():
                    chunks.append(ln.strip())
                i += 1
            out[key] = ' '.join(chunks).strip().strip('"\'')
            continue
        out[key] = rest.strip().strip('"\'')
        i += 1
    return out


# -- Discovery ---------------------------------------------------------------

def _glob_all(roots, pattern):
    paths = []
    for root in roots:
        if not root.is_dir():
            continue
        for p in root.glob(pattern):
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            paths.append(p)
    return paths


def _index_entry(canonical, aliases, description):
    """Aliases is a set including canonical, plus any other names the harness/user
    might invoke this tool with (e.g. plugin-namespaced form)."""
    return canonical, {'description': description, 'aliases': set(aliases) | {canonical}}


def _merge(out, entry):
    canonical, payload = entry
    if canonical not in out:
        out[canonical] = payload


def discover_skills(cwd):
    """Skill canonical name = directory name (matches what the harness exposes).

    Aliases are ONLY the canonical name itself and, for plugin skills, the
    `<plugin>:<canonical>` form. The frontmatter `name:` field is intentionally
    NOT aliased — some skills (e.g. gstack-*) use a bare `name:` for internal
    naming that does NOT match what the harness invokes them as, so trusting it
    would collapse genuinely-different tools into one row."""
    out = {}
    plugin_cache = Path.home() / '.claude' / 'plugins' / 'cache'

    for root in [Path.home() / '.claude' / 'skills', cwd / '.claude' / 'skills']:
        for skill_md in _glob_all([root], '*/SKILL.md'):
            fm = parse_frontmatter(skill_md)
            canonical = skill_md.parent.name
            _merge(out, _index_entry(canonical, {canonical}, fm.get('description', '')))

    for skill_md in _glob_all([plugin_cache], '*/*/*/skills/*/SKILL.md'):
        fm = parse_frontmatter(skill_md)
        canonical = skill_md.parent.name
        plugin_name = skill_md.parents[3].name
        aliases = {canonical, f'{plugin_name}:{canonical}'}
        _merge(out, _index_entry(canonical, aliases, fm.get('description', '')))

    return out


def discover_agents(cwd):
    out = {}
    plugin_cache = Path.home() / '.claude' / 'plugins' / 'cache'

    for root in [Path.home() / '.claude' / 'agents', cwd / '.claude' / 'agents']:
        for agent_md in _glob_all([root], '*.md'):
            fm = parse_frontmatter(agent_md)
            canonical = agent_md.stem
            _merge(out, _index_entry(canonical, {canonical}, fm.get('description', '')))

    for agent_md in _glob_all([plugin_cache], '*/*/*/agents/*.md'):
        fm = parse_frontmatter(agent_md)
        canonical = agent_md.stem
        plugin_name = agent_md.parents[2].name
        aliases = {canonical, f'{plugin_name}:{canonical}'}
        _merge(out, _index_entry(canonical, aliases, fm.get('description', '')))

    return out


def discover_commands(cwd):
    out = {}
    plugin_cache = Path.home() / '.claude' / 'plugins' / 'cache'

    for root in [Path.home() / '.claude' / 'commands', cwd / '.claude' / 'commands']:
        for cmd_md in _glob_all([root], '*.md'):
            fm = parse_frontmatter(cmd_md)
            canonical = cmd_md.stem
            _merge(out, _index_entry(canonical, {canonical}, fm.get('description', '')))

    for cmd_md in _glob_all([plugin_cache], '*/*/*/commands/*.md'):
        fm = parse_frontmatter(cmd_md)
        canonical = cmd_md.stem
        plugin_name = cmd_md.parents[2].name
        aliases = {canonical, f'{plugin_name}:{canonical}'}
        _merge(out, _index_entry(canonical, aliases, fm.get('description', '')))

    return out


# -- Rendering ---------------------------------------------------------------

def _escape_cell(s):
    return s.replace('|', '\\|').replace('\n', ' ').strip()


ONELINER_MAX = 100


def _to_oneliner(desc):
    """Collapse a description to a single short sentence: first sentence, capped
    at ONELINER_MAX chars with an ellipsis if it overflows."""
    if not desc:
        return ''
    flat = ' '.join(desc.split())  # collapse all whitespace runs
    # Take everything up to the first ". " (sentence end). Skip trailing period.
    end = flat.find('. ')
    sentence = flat[:end] if end != -1 else flat.rstrip('.')
    if len(sentence) > ONELINER_MAX:
        sentence = sentence[:ONELINER_MAX - 1].rstrip() + '…'
    return sentence


def _alias_map(index):
    """Flatten a discovery index to {alias_name: canonical_name}."""
    out = {}
    for canonical, payload in index.items():
        for alias in payload['aliases']:
            out[alias] = canonical
    return out


def normalize_counts(counts, skills, agents, commands):
    """Collapse alias names (e.g. `<plugin>:<name>`) to their canonical name
    using the disk discovery, so the used-tools table shows one row per tool
    even when the same skill was invoked via multiple aliases.

    Slash-commands can come from a `commands/*.md` file OR from any skill
    (every skill is invokable as `/<name>` or `/<plugin>:<name>`), so the
    slash-cmd alias map is the union of both."""
    aliases_by_kind = {
        'skill': _alias_map(skills),
        'agent': _alias_map(agents),
        'slash-cmd': {**_alias_map(commands), **_alias_map(skills)},
    }
    out = Counter()
    for (kind, name), n in counts.items():
        canonical = aliases_by_kind.get(kind, {}).get(name, name)
        out[(kind, canonical)] += n
    return out


def render_usage_table(counts):
    print('| Type | Name | Count |')
    print('|------|------|------:|')
    grouped = defaultdict(list)
    for (kind, name), n in counts.items():
        grouped[kind].append((name, n))
    for kind in TYPE_ORDER:
        rows = sorted(grouped.get(kind, []), key=lambda r: (-r[1], r[0]))
        for name, n in rows:
            print(f'| {kind} | {name} | {n} |')


def _is_used(kind, payload, counts):
    return any((kind, alias) in counts for alias in payload['aliases'])


def render_unused_table(skills, agents, commands, counts):
    items = []
    for name, payload in skills.items():
        if not _is_used('skill', payload, counts):
            items.append(('skill', name, payload['description']))
    for name, payload in agents.items():
        if not _is_used('agent', payload, counts):
            items.append(('agent', name, payload['description']))
    for name, payload in commands.items():
        if not _is_used('slash-cmd', payload, counts):
            items.append(('slash-cmd', name, payload['description']))
    type_rank = {k: i for i, k in enumerate(TYPE_ORDER)}
    items.sort(key=lambda r: (type_rank.get(r[0], 99), r[1].lower()))
    if not items:
        print('_No unused tools — every available tool was invoked at least once._')
        return
    print('| Type | Name | Description |')
    print('|------|------|-------------|')
    for kind, name, desc in items:
        print(f'| {kind} | {name} | {_escape_cell(_to_oneliner(desc))} |')


# -- Main --------------------------------------------------------------------

def main(argv):
    args = [a for a in argv[1:] if a]
    show_unused = False
    period = '30d'
    seen_period = False
    for arg in args:
        if arg in ('--unused', '-u'):
            show_unused = True
        elif arg in ('--no-unused',):
            show_unused = False
        elif not seen_period:
            period = arg
            seen_period = True
        else:
            print(f'Unexpected argument: {arg}', file=sys.stderr)
            return 1

    delta, label = parse_period(period)
    if delta is False:
        print(label, file=sys.stderr)
        return 1

    cutoff_iso = None
    if delta is not None:
        cutoff_iso = (datetime.now(timezone.utc) - delta).strftime('%Y-%m-%dT%H:%M:%SZ')

    counts, total, log_dir, has_files = aggregate_logs(cutoff_iso)

    # Discovery is needed both to canonicalize log entries (collapse plugin-
    # namespaced aliases into a single row) and to render the unused table.
    cwd = Path.cwd()
    skills = discover_skills(cwd)
    agents = discover_agents(cwd)
    commands = discover_commands(cwd)
    counts = normalize_counts(counts, skills, agents, commands)

    print(f'# Tool usage — {label}')
    print()
    if not has_files:
        print(f'No usage logs found in {log_dir} yet.')
        print('The hooks will populate logs on the next Skill, Agent, or slash-command invocation.')
        print()
    else:
        render_usage_table(counts)
        print()
        print(f'_Total invocations: {total} — source: `{log_dir}`_')
        print()

    if show_unused:
        print(f'## Unused tools — available but not invoked in {label}')
        print()
        print(f'_Discovered from `~/.claude/`, plugin cache, and `{cwd}/.claude/`._')
        print()
        render_unused_table(skills, agents, commands, counts)
    else:
        print('_Pass `--unused` to also list available tools that were not invoked in this period._')

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
