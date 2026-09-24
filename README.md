# savoir-faire

Personal, general-purpose agent skills. Self-contained: no shared config, no
dependency on another skill library.

## Install

```bash
npx skills add olivergg/savoir-faire -g --skill <name>   # or --all
```

## Skills

| Skill | Use |
|-------|-----|
| `all-sessions-recap` | Repo-by-repo recap across all Claude Code sessions |
| `concise-output` | Standing concise-output preference |
| `token-economy` | Cut token spend during a session |
| `guided-walkthrough` | Step-by-step explanation with a pause after each step |
| `nrepl-runtime-audit` | Verify a running JVM app's behavior via a Clojure nREPL |
| `jmh-microbench` | Standalone JMH microbenchmarks |
| `factual-report-latex` | French PDF reports in teal style via LaTeX/tectonic |
| `session-secret-audit` | Scan session transcripts for leaked secrets |

## License

Apache-2.0 — see `LICENSE`.
