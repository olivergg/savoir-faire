---
name: concise-output
description: >-
  Use this skill whenever about to write for this user — commit messages,
  javadoc/docstrings, code comments, chat explanations, PR/Jira comments,
  reports — because concise, low-fluff output is their standing GLOBAL
  preference, applied by default even when not asked this turn. Also when they
  ask to shorten something: concis, raccourcis, condense, synthétise, va à
  l'essentiel, sois bref, pas de blabla, TL;DR, too long, no fluff.
metadata:
  author: Olivier G
---

Recurring, repeated feedback across many sessions/projects. Default to this without being
asked — asking "shorter?" after the fact wastes a round-trip.

## Rules by category

**Commit messages** — the bare change; a short why only if it looks wrong without it (revert,
workaround, version pin), never guessed. No ceremony, no restating the diff line by line. 1-2 lines per bullet max. Respect existing repo conventions (ticket number, prefixes) but
strip everything not load-bearing.

**Javadoc / docstrings** — say what isn't obvious from the signature; never restate the method
name in prose. No lengthy doc for simple/internal code — reserve real javadoc for public API
surfaces users actually need.

**Code comments** — don't narrate what the code already says. Explanatory comments on
non-obvious logic only, translated to English, 1-2 lines. Prefer compact modern-language idioms
(var, switch expressions, streams) over verbose boilerplate — as long as readability doesn't
suffer.

**Tests** — compact given/when/then style, English, one clear assertion block per case; merge
near-duplicate test methods rather than stacking near-identical ones.

**Conversational explanations / investigation reports** — lead with the answer. Bullet points
over prose. State only what changed since last check (nothing changed → say so in one line).
No AI-report verbosity/fluff.

**PR / Jira comments** — a few lines max, plain and factual, no filler intro/outro.

**Reports/documents (managerial, one-pagers, cheat sheets)** — must be skimmable in one pass: a
single consolidated doc/table over scattered prose, clear/precise/concise/compact, no filler.

## Apply by default

Don't wait for "be concise" every time — it's this user's baseline. When in doubt, cut a draft
pass by another 30-50% before sending; keep numbers, code, and decisions, drop restating context
already known to the reader.
