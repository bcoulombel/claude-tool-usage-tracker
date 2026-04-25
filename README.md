# tool-usage-tracker

A small Claude Code plugin that logs every `Skill` and `Agent` (subagent/Task) tool invocation to a local JSONL file, and ships a skill that turns the log into an on-demand markdown report.

Built because Claude's built-in analytics dashboards (Team / Enterprise) don't break down usage per skill or per agent — and sometimes you want to know which skills are pulling their weight and which ones never trigger.

## What it does

- **PreToolUse hook** matching `Skill|Task` appends one JSONL line per invocation to:
  ```
  ~/.claude/local-telemetry/tools/YYYY-MM.jsonl
  ```
  One file per month. Plain text. Stays on your machine — never uploaded.

- **`skill-usage-tracker` skill** runs an aggregation script and prints a markdown table grouped by name with counts. Three preset periods: all-time, last 30 days, last 7 days.

## Install

From inside Claude Code:

```
/plugin install <owner>/<repo>
```

(replace with the GitHub `owner/repo` where this is hosted)

## Use

Just ask Claude in any session:

> Show me a tool usage report for the last 7 days

> Top skills all-time

> What agents have I used this month?

The skill recognises the period in plain English, runs the report script, and prints something like:

```
# Tool usage — last 30 days

| Name | Kind | Count |
|------|------|------:|
| lnb-build-frontend | skill | 42 |
| Explore | agent | 31 |
| lnb-review-pr | skill | 18 |
| general-purpose | agent | 12 |
...

_Total invocations: 187 — source: /Users/you/.claude/local-telemetry/tools_
```

## Storage

```
~/.claude/local-telemetry/
└── tools/
    ├── 2026-04.jsonl
    ├── 2026-05.jsonl
    └── ...
```

Each line is one tool call:

```json
{"ts":"2026-04-25T12:34:56Z","cwd":"/path/to/project","session_id":"...","tool":"Skill","skill":"lnb-build-frontend","subagent":null,"description":null}
```

At ~100 tool calls/day this comes out to roughly 1 MB/month — negligible. No rotation needed; old months are kept indefinitely so all-time reports work.

## Requirements

- macOS or Linux
- `jq` on your `PATH` (used by both the logger and the report script)
- Claude Code with plugin support

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
