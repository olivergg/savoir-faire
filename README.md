# savoir-faire

Personal, general-purpose agent skills. Self-contained: no shared config, no
dependency on another skill library.

## Install

```bash
npx skills add <source> -g --skill '*' -a claude-code github-copilot mistral-vibe -y
```

- Public repo: `<source>` = `olivergg/savoir-faire`
- Private repo: an SSH URL whose key has access, e.g. `git@github.com:olivergg/savoir-faire.git`

## Update

Edit here → commit → push → update (reuses the source recorded at install):

```bash
npx skills update all-sessions-recap concise-output factual-report-latex guided-walkthrough jmh-microbench nrepl-runtime-audit second-pass session-secret-audit token-economy -g -y
```

`-g` alone updates *every* global skill, whatever the cwd — hence the names.
Don't edit `~/.agents/skills` or install from a local path: neither is tracked
for updates.

## Skills

| Skill | Use |
|-------|-----|
| `all-sessions-recap` | Repo-by-repo recap across all Claude Code sessions |
| `concise-output` | Standing concise-output preference (prose, commits, docs) |
| `second-pass` | Cut a first draft of code down — delete, reuse, hoist, compact — at equal behavior |
| `token-economy` | Cut token spend during a session |
| `guided-walkthrough` | Step-by-step explanation with a pause after each step |
| `nrepl-runtime-audit` | Verify a running JVM app's behavior via a Clojure nREPL |
| `jmh-microbench` | Standalone JMH microbenchmarks |
| `factual-report-latex` | French PDF reports in teal style via LaTeX/tectonic |
| `session-secret-audit` | Scan session transcripts for leaked secrets |

## License

Apache-2.0 — see `LICENSE`.
