---
name: token-economy
description: Reduces input/output token spend during a Claude Code session by combining terse replies, file+grep instead of raw tool-output dumps, subagent delegation for wide exploration, and compact tabular encoding only for inter-tool payloads. Use when user says "save tokens", "token economy", "reduce cost", "be efficient with tokens", invokes /token-economy, or the session involves large repos and verbose shell output (git log, mvn, grep across many files).
metadata:
  author: Olivier G
---

# token-economy

Combines existing levers, adds discipline none of them cover alone.

## Quick start

1. Terse replies for the rest of the session: drop filler, pleasantries, hedging and restated context; fragments are fine; keep technical terms, numbers, code and paths exact.
2. Any shell/tool output over ~30 lines: redirect to a scratchpad file, read back only the decisive slice (`grep`, `tail`, `head -n`) — never the raw dump.
3. Exploration spanning more than 3 files, or an open-ended "how does X work": delegate to an Agent (Explore/general-purpose subagent), not inline reads in the main thread.
4. Structured/tabular data destined for another tool call or subagent: encode compactly — field names once in a header, one row per line (TOON `items[2]{id,name}:` or CSV), not repeated-key JSON. Data destined for the user's chat window: normal markdown.

## Gotchas

- Terse mode compresses chat replies only. Code, commit messages, docs, PR/issue text, memory files stay full prose — compressing those degrades a persisted artifact nobody re-reads token-by-token, for zero session-token benefit.
- Compact encoding saves tokens on the *next model's input*, not screen space. Using it in a chat reply trades token cost for human reading time — worse trade for the user, who reads every reply.
- A full stack trace or full file dump is rarely the actual ask. Quote the one decisive line (exception message, failing assertion, first differing diff line) and point at file/line for the rest.
- Don't re-summarize context already established earlier in the same conversation — that's the opposite of saving tokens.
- Redirecting output to a file only saves tokens if you then read back a *slice*. Reading the whole redirected file back defeats the point.

## Defaults

- Redirect-to-file threshold: ~30 lines of raw output. Below that, inline is cheaper than a round trip through a file.
- Delegation threshold: more than 3 files, or scope genuinely unclear up front.
