---
name: session-secret-audit
description: >-
  Use this skill when periodically auditing Claude Code session transcripts
  (~/.claude/projects/**) for leaked secrets — API keys, tokens, DB connection
  strings — and cleaning them up via pattern-based redaction, quarantine, or
  shredding. Also triggers for: session audit, leaked secrets, scan sessions,
  clean up transcripts, secret in session, redact session, rotate keys,
  find leaked credentials.
compatibility: Requires python3 (stdlib only, no deps)
metadata:
  author: Olivier G
---

## Gotchas

- **Never verify a match by printing it** — no `awk '{print}'`, no `sed -n`, no
  `cat`/`head` of the matched span, not even "just to check the length." Any
  command whose output includes the actual secret writes that secret straight
  into *this* session's transcript — the exact failure this skill exists to
  clean up. Use `scripts/scan_secrets.py scan` (counts only) or `redact
  --dry-run` (match counts only) to verify — never a raw grep/read of the hit.
  The script has no "reveal" mode; that's intentional, not a missing feature.
- **Redact by pattern, never by literal value.** If you ever catch yourself
  about to paste the actual secret string into a `sed`/`perl`/`grep` command
  to remove it, stop — that reproduces the leak in the command's own
  transcript. `scripts/scan_secrets.py redact` substitutes by regex shape only.
- **The active/current session file is fair game too.** If the audit finds a
  leak in the transcript of the conversation you're currently having (it
  happens — e.g. a careless verification command), redact it same as any
  other file. Tell the user first since it's live.
- **Redaction ≠ rotation.** Once a secret has touched disk in plaintext, the
  exposure already happened. Redacting/shredding the transcript prevents
  *future* reads; it does not undo the leak. Always tell the user to rotate
  the credential regardless of what cleanup is done.
- **Ask before destructive actions.** Quarantine (move) is reversible;
  `redact` overwrites file content in place; `shred` is irreversible. Default
  to `scan` first, show the user a recap table, and confirm before `redact`
  or `shred` — don't chain them automatically.
- **SSD/APFS caveat**: `shred` does multi-pass overwrite but copy-on-write
  filesystems don't guarantee the old blocks are physically gone. It's
  best-effort, not a substitute for rotating the credential.
- **False positives are common**: `private_key_block` matches Helm chart doc
  comments (`## -----BEGIN RSA PRIVATE KEY-----`) as often as real keys;
  `db_connection_string` matches local dev creds (`app_user@localhost`)
  constantly — low real risk. Read the severity column, not just the count.

## Workflow

### 1. Scan

```bash
python3 scripts/scan_secrets.py scan
```

Prints a table: severity, pattern name, match count, file mtime, path —
**no secret values, ever**. Sorted by severity (critical first), then most
recent first.

Turn this into a recap table for the user grouped by finding, e.g.:

| # | Secret | Where | Severity | Rotated? |
|---|--------|-------|----------|----------|

One row per distinct credential, not per file — the same key often leaks
across several sessions (e.g. a project's own transcript plus its subagents).

### 2. Decide per finding, with the user

For each row, ask whether to:
- **redact** — best default; keeps the rest of the conversation history,
  removes just the secret shape. Preserves unrelated context.
- **quarantine** — move the whole file out of `~/.claude/projects` (e.g. to
  `~/.claude/quarantine/`) without deleting, if the transcript itself is
  low-value and you'd rather just get it out of the scanned tree.
- **shred** — irreversible destroy. Only when the transcript content itself
  isn't worth keeping (e.g. it's weeks old, routine, nothing else in it
  matters) — confirm the file's age/relevance first (`stat -f "%Sm"`).

### 3. Redact (pattern-based, safe)

```bash
python3 scripts/scan_secrets.py redact \
  --patterns anthropic_api_key slack_token \
  -- /path/to/session.jsonl [more files...]
```

`--dry-run` first to get a match count without modifying anything. Omitting
`--patterns` redacts every pattern this skill knows about — usually you want
to scope it to just the finding(s) you're clearing.

### 4. Quarantine (reversible move)

```bash
python3 scripts/scan_secrets.py quarantine \
  /path/to/session.jsonl [more files...]
# default dest: ~/.claude/quarantine/
```

### 5. Shred (irreversible, last resort)

```bash
python3 scripts/scan_secrets.py shred \
  /path/to/session.jsonl [more files...]
```

### 6. Tell the user what still needs rotating

List every distinct credential found as critical/high severity and confirmed
real (not a false positive) — cleanup doesn't replace rotation. Leave the
"Rotated?" column in the recap table for the user to fill in; this skill has
no way to check rotation status against the external service.

## Extending patterns

New secret shapes go in `PATTERNS` at the top of `scripts/scan_secrets.py` —
`name -> (regex, severity)`. Keep regexes shape-based (prefix + length), never
tied to one real value. Test a new pattern with `redact --dry-run` on a
throwaway copy before trusting it against real sessions.
