# tool-usage-tracker

A small Claude Code plugin that logs every `Skill` and `Agent` (subagent/Task) tool invocation to a local JSONL file, and ships a skill that turns the log into an on-demand markdown report.

Built because Claude's built-in analytics dashboards (Team / Enterprise) don't break down usage per skill or per agent — and sometimes you want to know which skills are pulling their weight and which ones never trigger.

## What it does

Three things get tracked, all to one local JSONL file:

- **`Skill` tool calls** — when Claude decides to invoke a skill mid-conversation. Captured by a `PreToolUse` hook.
- **Subagent runs** (built-in `Explore`/`Plan`/`general-purpose` and custom `.claude/agents/*.md`). Captured by a `SubagentStop` hook that fires once per subagent completion. More reliable than `PreToolUse` on the `Agent` tool, which empirically misses custom subagents.
- **Slash commands** typed by you (`/lnb-review-pr`, `/plugin`, etc.) — these expand inline and don't go through the Skill tool, so they're caught by a separate `UserPromptSubmit` hook.

All three append to:
```
~/.claude/local-telemetry/tools/YYYY-MM.jsonl
```
One file per month. Plain text. Stays on your machine — never uploaded.

The bundled **`skill-usage-tracker` skill** runs an aggregation script and prints a markdown report:

- **Used tools** (always shown) — grouped by Type (`agent` → `skill` → `slash-cmd`), sorted by count.
- **Unused tools** (opt-in, ask for it) — every Skill/Agent/slash-command found on disk (in `~/.claude/`, the plugin cache, and `<cwd>/.claude/`) that wasn't invoked in the period, with one-liner descriptions pulled from each tool's frontmatter. Off by default because the list is long; ask the skill for "unused tools" or "what haven't I used" to include it.

Period accepts `all` or any `<N>[h|d|w|m]` (e.g. `1h`, `1d`, `7d`, `14d`, `30d`, `2w`, `3m`). Default: `30d`.

## Install

From inside Claude Code, add this repo as a marketplace, then install the plugin from it:

```
/plugin marketplace add bcoulombel/claude-tool-usage-tracker
/plugin install tool-usage-tracker@bcoulombel
```

Verify with:

```
/plugin list
```

To update later: `/plugin marketplace update bcoulombel` then `/plugin install tool-usage-tracker@bcoulombel` again.

## Use

Just ask Claude in any session:

> Show me a tool usage report for the last 7 days

> Top skills all-time

> What agents have I used this month?

The skill recognises the period in plain English, runs the report script, and prints something like:

```
# Tool usage — last 30 days

| Type | Name | Count |
|------|------|------:|
| agent | Explore | 31 |
| agent | general-purpose | 12 |
| skill | lnb-build-frontend | 42 |
| skill | lnb-review-pr | 18 |
| slash-cmd | ship | 6 |
...

_Total invocations: 187 — source: /Users/you/.claude/local-telemetry/tools_

_Pass `--unused` to also list available tools that were not invoked in this period._
```

Ask for unused explicitly ("what haven't I used this month?") and you also get:

```
## Unused tools — available but not invoked in last 30 days

| Type | Name | Description |
|------|------|-------------|
| agent | lnb-rename-auditor | Catches missed references when a PR renames a symbol |
| skill | gstack-canary | Post-deploy canary monitoring |
...
```

## Storage

```
~/.claude/local-telemetry/
└── tools/
    ├── 2026-04.jsonl
    ├── 2026-05.jsonl
    └── ...
```

Each line is one invocation. Three shapes:

```json
{"ts":"...","tool":"Skill","skill":"lnb-build-frontend","subagent":null,"slash_command":null, ...}
{"ts":"...","tool":"SubagentStop","skill":null,"subagent":"Explore","slash_command":null,"stop_reason":"completed", ...}
{"ts":"...","tool":"SlashCommand","skill":null,"subagent":null,"slash_command":"lnb-review-pr", ...}
```

At ~100 tool calls/day this comes out to roughly 1 MB/month — negligible. No rotation needed; old months are kept indefinitely so all-time reports work.

## Requirements

- **`python3` on `PATH`** — both the hook and the report script are written in Python 3 using only the standard library (no `pip install` needed).
  - **macOS 12.3+**: ships with `/usr/bin/python3` out of the box. Nothing to do.
  - **Older macOS**: install via `brew install python` or Xcode Command Line Tools.
  - **Linux**: `python3` is included on all major distros (Ubuntu, Debian, Fedora, Arch, Alpine).
  - **Windows**: untested. The hook command is `python3 ...` which usually doesn't resolve on Windows out of the box — you'd need to alias `python3` or edit `hooks/hooks.json`.
- **Claude Code** with plugin support (recent versions).

If `python3` is missing, the hook fails silently and your tool calls keep working as normal — you just won't get any logs until it's available.

## Uninstall

```
/plugin uninstall tool-usage-tracker
```

Logs are not deleted automatically. If you want to wipe them:

```bash
rm -rf ~/.claude/local-telemetry/tools
```

## Privacy

Everything is local. The hook writes to your home directory only. The plugin makes no network calls. The repo contains the *mechanism*, not your data.

## License

MIT
