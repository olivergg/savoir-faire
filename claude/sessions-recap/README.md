# sessions-recap

Claude Code mod: a pane ranking your Claude Code sessions across every project, the interactive face of the
`all-sessions-recap` skill.

- Ranking over 1, 7 or 14 days, flat by session or grouped by project (`g`), sorted by score or recency (`s`).
- Search across all turns; expand a project to see its sessions; one-line summary of a session on demand.
- `r` refreshes; `/sessions-recap` opens the pane.

Needs the `all-sessions-recap` skill installed globally (it runs its `scripts/session_recap.py` from
`~/.agents/skills/`), and `python3`. Summaries are a short Haiku call billed to your session.

## Install

```
npx skills add olivergg/savoir-faire -g --skill all-sessions-recap -a claude-code -y
claude plugin marketplace add olivergg/savoir-faire
claude plugin install sessions-recap@savoir-faire
```
