---
name: skill-usage-tracker
description: Report on Skill, Agent, and slash-command usage tracked by the tool-usage-tracker plugin. Use when the user asks for a usage report, "top skills", or activity over a period (all-time, last 30 days, last 7 days).
---

# skill-usage-tracker

Aggregates the JSONL files written by the `tool-usage-tracker` plugin's PreToolUse hook and prints a markdown report.

## How to use

Run the bundled report script with the requested period:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/bin/report.py" [period]
```

Where `period` is one of:

| User says... | Pass... |
|---|---|
| "all-time", "everything", "ever", or no period given | `all` |
| "last 7 days", "this week", "past week" | `7d` |
| "last 30 days", "last month", "this month" (default) | `30d` |

Pass the script's stdout through to the user as-is — it's already formatted markdown.

## Examples

- "show me a usage report" → `report.py 30d`
- "what skills did I use this week?" → `report.py 7d`
- "top skills all-time" → `report.py all`

## Notes

- Logs live at `~/.claude/local-telemetry/tools/YYYY-MM.jsonl` and are local to the user's machine.
- If the script reports no logs found, the hooks haven't captured anything yet — tell the user to invoke a Skill, Agent, or slash command and try again.
- The report shows three kinds:
  - `skill` — `Skill` tool calls (Claude decides to invoke a skill mid-conversation)
  - `agent` — `Agent`/`Task` tool calls (subagent dispatch)
  - `slash-cmd` — slash commands typed by the user (`/lnb-review-pr`, `/plugin`, etc.) — these expand inline and don't go through the Skill tool, so they're tracked separately by a `UserPromptSubmit` hook.
