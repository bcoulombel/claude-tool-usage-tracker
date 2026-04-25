---
name: skill-usage-tracker
description: Report on Skill and Agent (subagent/Task) tool usage tracked by the tool-usage-tracker plugin. Use when the user asks for a usage report, "top skills", or activity over a period (all-time, last 30 days, last 7 days).
---

# skill-usage-tracker

Aggregates the JSONL files written by the `tool-usage-tracker` plugin's PreToolUse hook and prints a markdown report.

## How to use

Run the bundled report script with the requested period:

```bash
${CLAUDE_PLUGIN_ROOT}/bin/report.sh [period]
```

Where `period` is one of:

| User says... | Pass... |
|---|---|
| "all-time", "everything", "ever", or no period given | `all` |
| "last 7 days", "this week", "past week" | `7d` |
| "last 30 days", "last month", "this month" (default) | `30d` |

Pass the script's stdout through to the user as-is — it's already formatted markdown.

## Examples

- "show me a usage report" → `report.sh 30d`
- "what skills did I use this week?" → `report.sh 7d`
- "top skills all-time" → `report.sh all`

## Notes

- Logs live at `~/.claude/local-telemetry/tools/YYYY-MM.jsonl` and are local to the user's machine.
- If the script reports no logs found, the hook hasn't captured anything yet — tell the user to invoke a Skill or Agent and try again.
- The report shows three kinds: `skill` (Skill tool calls), `agent` (Task/subagent calls), `other` (shouldn't appear unless the matcher is changed).
