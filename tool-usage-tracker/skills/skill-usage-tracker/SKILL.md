---
name: skill-usage-tracker
description: Report on Skill, Agent, and slash-command usage tracked by the tool-usage-tracker plugin. Use when the user asks for a usage report, "top skills", activity over a period (any duration — 1h, 1d, 7d, 30d, 2w, 3m, all), or wants to see which available tools they haven't used.
---

# skill-usage-tracker

Aggregates the JSONL files written by the `tool-usage-tracker` plugin's hooks and prints a markdown report. By default, only the **used tools** table is shown. Pass `--unused` to also list available tools that weren't invoked in the period (descriptions are truncated to a one-liner).

## How to use

Run the bundled report script:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/bin/report.py" [period] [--unused]
```

### `period`

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

The script accepts any value matching `all` or `^\d+[hdwm]$`. Default if no period is given: `30d`.

### `--unused` (opt-in)

Pass `--unused` ONLY when the user explicitly asks about unused/untouched/never-invoked tools. Default reports do NOT include this section because it's long.

Trigger phrases that should add `--unused`:
- "what haven't I used?"
- "show unused tools"
- "what tools haven't I tried?"
- "list every available skill"
- "include unused"
- "full report"

If the user just says "show me a usage report" or asks for top skills, leave it OFF.

Pass the script's stdout through to the user as-is — it's already formatted markdown.

## Examples

| User asks | Command |
|---|---|
| "show me a usage report" | `report.py 30d` |
| "what skills did I use this week?" | `report.py 7d` |
| "skill usage in the last hour" | `report.py 1h` |
| "top skills all-time" | `report.py all` |
| "what skills haven't I tried in the last month?" | `report.py 30d --unused` |
| "full usage report for the week, including unused" | `report.py 7d --unused` |
| "list every skill I've never invoked" | `report.py all --unused` |

## Output structure

1. **Used tools** — `Type | Name | Count`, grouped by Type in this order: `agent`, `skill`, `slash-cmd`. Within each Type, sorted by Count descending. Always shown.

2. **Unused tools — available but not invoked in <period>** — `Type | Name | Description`. Same Type grouping; alphabetical within each group. Descriptions truncated to a one-liner (first sentence, max 100 chars). Only shown when `--unused` is passed.

   "Available" = present on disk in any of:
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
