---
name: concise-output
description: >-
  Apply the user's standing preference for concise, low-fluff output —
  commit messages, javadoc/docstrings, code comments, conversational
  explanations, PR/Jira comments, and generated reports. This is a GLOBAL
  preference for this user, not a one-off request: apply it by default when
  writing any of the above, even if not explicitly asked this turn. TRIGGER
  when: concis, concision, compact, compresse, raccourcis, réduis, condense,
  synthétise, va à l'essentiel, sois bref, straight to the point, less
  verbose, too long, no fluff, sans fioriture, pas de blabla, en une ligne,
  TL;DR — or whenever about to write a commit message, javadoc, code comment,
  PR/Jira comment, a chat explanation, or a report/document for this user.
metadata:
  author: Olivier G
---

Recurring, repeated feedback across many sessions/projects. Default to this without being
asked — asking "shorter?" after the fact wastes a round-trip.

## Rules by category

**Commit messages** — what + why, nothing else. No ceremony, no restating the diff line by line.
1-2 lines per bullet max. Respect existing repo conventions (ticket number, prefixes) but
strip everything not load-bearing.
> "make the commit message more compact concise, less ceremony, explain the what and why, still
> bullet list, but one or two lines max each"

**Javadoc / docstrings** — say what isn't obvious from the signature; never restate the method
name in prose. No "à rallonge" doc for simple/internal code — reserve real javadoc for public API
surfaces users actually need.
> "rendre beaucoup plus concis la javadoc et les commentaires" / "Pas de javadoc à rallonge"

**Code comments** — don't narrate what the code already says. Explanatory comments on
non-obvious logic only, translated to English, 1-2 lines. Prefer compact modern-language idioms
(var, switch expressions, streams) over verbose boilerplate — as long as readability doesn't
suffer.
> "trop de commentaires de code, pas assez concis et compact" / "rendre plus compact le code tout
> en le laissant lisible et documenté"

**Tests** — compact given/when/then style, English, one clear assertion block per case; merge
near-duplicate test methods rather than stacking near-identical ones.
> "rendre plus compact le tests, avoir given/when/then ?"

**Conversational explanations / investigation reports** — lead with the answer. Bullet points
over prose. State only what changed since last check ("si rien n'a changé, dis-le en une ligne").
No AI-report verbosity/fluff ("pas de verbiage IA").
> "Vraiment à l'essentiel stp, Bullet list, concis" / "this too much text, can we compress again"

**PR / Jira comments** — a few lines max, plain and factual, no filler intro/outro.
> "commentaire...très concis" / "pas de fioriture stp"

**Reports/documents (managerial, one-pagers, cheat sheets)** — must be skimmable in one pass: a
single consolidated doc/table over scattered prose, clear/precise/concise/compact, no filler.
> "consolider tout ça dans un seul document, clair, précis, concis, compact, compressé, sans
> fioriture" / "fais un tableau, plus clair, plus concis"

## Apply by default

Don't wait for "be concise" every time — it's this user's baseline. When in doubt, cut a draft
pass by another 30-50% before sending; keep numbers, code, and decisions, drop restating context
already known to the reader.
