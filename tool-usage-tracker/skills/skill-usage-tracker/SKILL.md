---
name: skill-usage-tracker
description: Report on Skill, Agent, and slash-command usage tracked by the tool-usage-tracker plugin. Use when the user asks for a usage report, "top skills", activity over a period (any duration — 1h, 1d, 7d, 30d, 2w, 3m, all), or wants to see which available tools they haven't used.
---

# skill-usage-tracker

Aggregates the JSONL files written by the `tool-usage-tracker` plugin's hooks and prints a markdown report. Two tables: **used tools** (grouped by Type) and **unused tools** (available on disk but never invoked in the period).

## How to use

Run the bundled report script with the requested period:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/bin/report.py" [period]
```

Where `period` is one of:

| User says... | Pass... |
|---|---|
| "all-time", "everything", "ever" | `all` |
| "last 1 hour", "past hour" | `1h` |
| "today", "last day", "last 24 hours" | `1d` |
| "this week", "last 7 days" | `7d` |
| "last 30 days", "this month" (default) | `30d` |
| "last 2 weeks" | `2w` |
| "last 3 months" | `3m` |
| any other duration | `<N>[h|d|w|m]` |

The script accepts any value matching `all` or `^\d+[hdwm]$` — no need to constrain the user to fixed buckets. Default if no period is given: `30d`.

Pass the script's stdout through to the user as-is — it's already formatted markdown.

## Examples

- "show me a usage report" → `report.py 30d`
- "what skills did I use this week?" → `report.py 7d`
- "skill usage in the last hour" → `report.py 1h`
- "top skills all-time" → `report.py all`
- "what skills haven't I tried in the last month?" → `report.py 30d` (the unused section answers this)

## Output structure

The report has two sections:

1. **Used tools** — `Type | Name | Count`, grouped by Type in this order: `agent`, `skill`, `slash-cmd`. Within each Type, sorted by Count descending.

2. **Unused tools — available but not invoked in <period>** — `Type | Name | Description`. Same Type grouping; alphabetical within each group. "Available" = present on disk in any of:
   - `~/.claude/{skills,agents,commands}/`
   - `~/.claude/plugins/cache/*/*/*/{skills,agents,commands}/`
   - `<cwd>/.claude/{skills,agents,commands}/` (current project)

   Discovery uses the directory name (not the `name:` frontmatter), because some skills use a bare name (`browse`) while the harness exposes the directory-prefixed form (`gstack-browse`). Plugin-namespaced aliases (`<plugin>:<name>`) are also matched against the logs.

## Notes

- Logs live at `~/.claude/local-telemetry/tools/YYYY-MM.jsonl` and are local to the user's machine.
- If the script reports no logs found, the hooks haven't captured anything yet — tell the user to invoke a Skill, Agent, or slash command and try again.
- The report shows three kinds:
  - `skill` — `Skill` tool calls captured by `PreToolUse` (Claude invokes a skill mid-conversation).
  - `agent` — subagent runs captured by `SubagentStop` after each subagent finishes. Covers both built-in subagent types (`Explore`, `general-purpose`, `Plan`...) and custom project-defined ones (`.claude/agents/*.md`). `SubagentStop` is more reliable than the `PreToolUse` hook on the `Agent` tool, which empirically misses custom subagents.
  - `slash-cmd` — slash commands typed by the user (`/lnb-review-pr`, `/plugin`...) captured by `UserPromptSubmit`. Slash commands expand inline and don't go through the `Skill` tool.
- Because the unused list is scoped to the current `cwd`, switching projects changes which project-local skills/agents/commands appear.
