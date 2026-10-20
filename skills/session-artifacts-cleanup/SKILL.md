---
name: session-artifacts-cleanup
description: >-
  Clean up a directory cluttered by files that past Claude Code sessions
  generated — reports, drafts, notes, exports, build outputs now obsolete or
  superseded. Cross-references session transcripts (~/.claude/projects/**)
  with the disk to tell which session created each file and when it was last
  used, groups versions of the same document, then archives (never deletes)
  one group at a time with the user's sign-off; reversible via a manifest.
  TRIGGER when: faire du ménage, nettoyer le dossier, rapports obsolètes,
  vieux fichiers, fichiers générés par Claude, trier les fichiers, archiver,
  ranger, clean up generated files, obsolete reports, stale drafts, declutter,
  session artifacts, leftover files from past sessions, superseded versions.
compatibility: Requires python3 ≥ 3.11 (stdlib only, no deps)
metadata:
  author: Olivier G
---

## Gotchas

- **`none` ≠ "the user's own file".** Claude Code purges transcripts after
  `cleanupPeriodDays` (default 30), so anything older has no surviving trace
  even if a session wrote it. Treat `none` as "origin unknown": judge on the
  content, and ask before proposing it.
- **Never delete, archive.** `archive` moves into `<dir>/_archive/<date>/` and
  logs the move in `_archive/MANIFEST.tsv`; `restore` puts it back. A report
  that looks obsolete is often the only copy of a decision or a number. Deleting
  stays a separate, explicit request from the user, on named paths.
- **Suggestions are leads, not verdicts.** `superseded?` only means "same
  family name, older date/mtime": `incident-a-0915.md` and `incident-b-1008.md`
  are different incidents, and a source dir and its build output share a
  family on purpose. Open both before calling one obsolete.
- **Source dir + build output = one unit.** `rapport-x/` (sources, build
  script) and `rapport-x-final.html` (its output) land in the same family.
  Archive both or neither, because the output can't be rebuilt without the
  sources, and the sources alone aren't what people read.
- **Git-tracked files are refused** by `archive`, because git history already
  keeps them; suggest `git rm` instead if the user wants them gone.
- **Don't read big files whole to judge them.** The `title` column and the
  first ~40 lines are enough to tell what a document is; large HTML reports
  burn context for nothing.

## Workflow

### 1. Inventory

```bash
python3 scripts/session_artifacts.py inventory <dir> > /tmp/inventory.md
```

One row per top-level entry (dirs aggregated); `--recursive` for one row per
file, `--stale-days N` (default 30), `--json` for the raw rows. Columns:

| Column | Meaning |
|---|---|
| `suggest` | `superseded?` (older version in a family) · `stale` (no mtime change nor real use for > N days) · `unknown` (no transcript trace) · `keep` · `tracked` (git) |
| `origin` | strongest trace: `written` (Write tool) > `bash` (redirect/`-o`/`tee`) > `edited` > `read` > `none` |
| `family` | name minus dates, `v2`, `final`, `draft`… ; build outputs take their source dir's family |
| `sessions` / `last_touch` | how many sessions really used it, last date. Not counted: one Bash command reading ≥ 3 entries (`ls`, `head` loop, `grep -r`: a survey), and any read from a session that ran this script (cleanup inspecting candidates) |
| `created_by` | first prompt of the session that wrote it, to recall why it exists |

### 2. Judge the candidates

For each `superseded?`, `stale` and `unknown` row, read its `title` and, when
ambiguous, the head of the file and of its newer sibling. Classify:

- **obsolete**: a newer version covers it (draft → final, J-2 journal → post-MEP report).
- **one-shot, done**: incident notes, PR messages, Slack drafts whose event is over: archive candidates, unless they are the only written record.
- **raw input**: logs, XML/test reports, exports: archive if a report already digests them.
- **keep**: still referenced, a reference doc, or unclear.

### 3. Recap table, then ask

Show one table grouped by family, proposed action per group, sizes:

| Family | Entries | Why | Proposal |
|---|---|---|---|

Ask which groups to archive. Don't chain all groups in one go, because one
wrong guess on a group is cheap to undo but a whole-folder sweep isn't
reviewable.

### 4. Archive the approved groups

```bash
python3 scripts/session_artifacts.py archive <dir> <entry> [<entry>...]
```

Paths relative to `<dir>` or absolute. Refuses: outside `<dir>`, already
archived, git-tracked, destination exists.

### 5. Report and how to undo

List what moved and the total size freed from the working view, then give the
undo command:

```bash
python3 scripts/session_artifacts.py restore <dir> _archive/<date>/<entry>
```
