---
name: all-sessions-recap
description: Use this skill when the user wants a global recap of what they're working on across all Claude Code projects — a repo-by-repo summary ranked by activity/usage. Also triggers for — sur quoi je suis, récap des sessions, résumé global, workspace recap, qu'est-ce que je fais en ce moment, activity across projects, all my sessions, project overview.
metadata:
  author: Olivier G
---

# all-sessions-recap

Reads every Claude Code session transcript under `~/.claude/projects/` (local,
read-only, no network) and answers "what am I actually working on right now,
across everything?" — grouped by repo, ranked by a recency-weighted score.

The script itself never calls an LLM — it only ranks and extracts. **The
actual recap is written by you**, the skill runner, from the extracted
material. Don't just print the auto-generated titles and stop there.

## Default flow: real per-session recaps

1. Run digest to get ranked projects + extracted human-turn material in one
   shot:
   ```bash
   python3 scripts/session_recap.py digest
   ```
   Defaults: last 7 days, top 15 projects by score, top 5 sessions per
   project, 6 sampled turns per session (first half + last half, noted if
   anything was cut). Tune with `--days`, `--limit`, `--top-titles`,
   `--max-turns`, `--sort {score,recent}`. If the user asks about a project
   you know is active but don't see in the output, it was likely cut by
   `--limit` — rerun with a higher one (or `recap --plain` first to see the
   full ranked list) before assuming it has no recent sessions.
2. For every session block in the output, write a real recap from its human
   turns + last assistant note — what was asked, what was explored/decided,
   where it landed. Ignore the `auto-title` line for this; it's just there
   as a hint, your recap should be better than it.
3. Present it compactly — this is a scan-the-room recap, not a report.
   Chat markdown can't render ANSI colors, so distinction between elements
   comes from emoji + markdown styling, each element consistently styled so
   the eye can jump straight to the piece it wants:
   - **Repo path**: bold (`**~/workspace/my-api**`), prefixed by a project
     emoji — same mapping the script uses for its own colored output
     (`EMOJI_RULES` in `scripts/session_recap.py`: front → 🎨,
     db/postgres/sql → 🗄️, kafka → 📨, infra/k8s/provisioning → ☸️,
     jenkins/cicd/pipeline → 🚀, e2e/test → 🧪, security/audit/secret → 🔐,
     skill → 🧭, doc → 📚, jira → 🎫, sso → 🔑, sonar → 🔎,
     map/position/gps → 🗺️, changelog → 📰, else → 📁) — keep it in sync if
     that list changes.
   - **Branch name**: inline code (`` `⎇ branch-name` ``) — code spans
     render in a visually distinct color/monospace/background in virtually
     every markdown client, which is what stands in for "a different color"
     here. Ahead/behind stays outside the code span, in plain text.
   - **Recap sentence**: italic (`*trimmed to the core decision/outcome*`).
   - A recency dot standing in for the script's color tiers: 🟢 < 3h,
     🟡 < 24h, ⚪ beyond that. Left as a plain emoji, not styled.

   **Group sessions by branch under each project**, one branch sub-header
   per branch (full name, never truncated — that's what gets it room to
   breathe without repeating it per session or wrapping a long recap line),
   sessions sharing that branch listed under it as one line each. Both
   `digest` and `recap` also compute the branch's ahead/behind count vs. the
   repo's main branch (local refs only, no fetch — cheap, shells out `git`
   once per distinct branch, skip with `--no-git-status` if it ever matters
   for speed) — append it after the branch name: `N↑` ahead only, `N↓`
   behind only, `N↑ M↓` both, nothing shown for the main branch itself or
   when git status can't be determined (deleted repo/branch, detached HEAD,
   no resolvable main):
   ```
   🧭 **~/workspace/my-skills**
     `⎇ main`
       🟢 maintenant — *<short recap>.*
       🟢 32m — *<short recap>.*

   📁 **~/workspace/my-api**
     `⎇ refactor/extract-query-module` (1↑)
       🟢 2h — *<short recap>.*
     `⎇ feature/PROJ-123-export-grid` (3↑)
       🟡 1d — *<short recap>.*
       🟡 1d — *<short recap>.*
   ```
   Keep branches in the order their most-recent session last appeared.
   Keep the session id available on request (not printed by default) in
   case the user wants to jump back into that session — the headline text
   is your recap, not the id and not the raw auto-title. If a recap can't
   be compressed to one line without losing the point, that's fine — better
   a two-line recap than a misleading one-liner — but default to one line.

If the user asks for more sessions on one project than the digest included,
re-run `show <session_id>` (below) for the specific ones needed — cheaper
than re-running digest with a larger `--top-titles` across every project.

## Fast path: no LLM, just the heuristic list

When the user wants speed over depth (e.g. "just the titles", "quick list"),
skip straight to:
```bash
python3 scripts/session_recap.py recap
```
Same ranking, but prints the AI-generated title Claude Code already assigned
each session instead of extracting/recapping anything — instant, no reading
required on your part. Flags: `--days`, `--limit`, `--top-titles`,
`--half-life`, `--sort`, `--topics` (title-only, no dot/time/branch/id),
`--plain` (force no color/emoji — auto when not a tty or `NO_COLOR` is set),
`--no-ids`.

## Excluding projects

Set `SESSION_RECAP_IGNORE` to colon-separated glob patterns (fnmatch,
matched against both the full cwd and its `~`-shortened form) to
permanently exclude project dirs, e.g.
`export SESSION_RECAP_IGNORE='~/scratch*:~/.vibe*'`. Applies to `recap` and `digest` both. Per-run: `--ignore
GLOB` (repeatable, additive) to exclude more without editing the file,
`--no-ignore` to see everything including the defaults.

## How the score works

For each project (grouped by the session's recorded `cwd`, not the encoded
directory name — more reliable when a path contains dashes), every session's
message count is decayed exponentially by its age (`--half-life` days, default
3.0), then summed. A project with one huge session yesterday can still
outrank a project with several small sessions from a week ago — intentional,
this tracks *current* focus, not lifetime volume.

## `show <session_id>` — deep dive on one session

```bash
python3 scripts/session_recap.py show <session_id>
```

Accepts a full id, an unambiguous prefix, or a direct path. Prints every
genuinely-typed human turn (filtered: no tool-call noise, no sidechain/
subagent transcripts, no attachments) plus the last assistant text note —
use when the digest's sampled turns aren't enough for a given session.
`--max-turns N` samples like digest does; omit for the full transcript.
`--json` gives the same data structured.

## Notes

- Nested subagent-transcript directories (same name as a session UUID) are
  skipped — only top-level `*.jsonl` files are read.
- A project with zero sessions inside the `--days` window is omitted
  entirely, not shown with a zero score.
- No config file needed — the root path is fixed (`~/.claude/projects`),
  overridable with `--root` for testing. Standalone skill, no dependency on
  any other skill or config resolution mechanism.
