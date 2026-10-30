---
name: shoulders-of-giants
description: >-
  Use this skill when the user invokes /shoulders-of-giants before designing or coding
  something: research ONLINE ONLY how others already solved the same problem —
  standards (RFC, W3C, ECMA, PEP/JEP), peer-reviewed papers, classic open books, mature
  open-source reference implementations — and bring back sourced, time-tested patterns,
  trade-offs and pitfalls instead of the hype of the moment. Open, free sources only;
  every citation fetched and quoted, never from memory. Manual only.
disable-model-invocation: true
metadata:
  author: Olivier G
---

# shoulders-of-giants

> "Bernard of Chartres used to compare us to dwarfs perched on the shoulders of giants."
> — John of Salisbury, *Metalogicon* III.4 (1159)
>
> "If I have seen further it is by standing on ye sholders of Giants." — Newton, letter
> to Hooke (5 Feb 1675/6)
>
> "Whereas Newton could say, 'If I have seen a little farther than others, it is because
> I have stood on the shoulders of giants,' I am forced to say, 'Today we stand on each
> other's feet.'" — Hamming, *One Man's View of Computer Science*, Turing Award lecture (1968)

Most "new" problems in software were named, solved and argued over decades ago — under
another name. The aim is to find that lineage, not the latest blog post: the **Lindy
effect** (an idea that has survived N years is likely to survive N more) is the filter.

## Hard rules

- **Online only.** Sources come from WebSearch/WebFetch. Never search the local disk,
  repo or other projects for "how it was done". Local context may only *frame* the
  question, and only if the user points to it.
- **Open only.** Every source must be readable free and legally online: no paywall, no
  login wall, no shadow libraries. A paywalled classic counts only through a legal free
  copy (author preprint, arXiv, author's homepage, institutional repository) — otherwise
  it's out, even if famous.
- **Fetched, not remembered.** Every citation is opened in this session and backed by a
  short quote or section number. A reference recalled from memory but not fetched is
  dropped, or listed under "not verified". Never invent a DOI, an RFC number, a page.
- **Established, not trending.** See the Lindy screen (§4).

## Source tiers

| Tier | Source | Where (examples) |
|------|--------|------------------|
| ★★★ | **Standards & specs** | rfc-editor.org / datatracker.ietf.org, w3.org/TR, whatwg.org, ecma-international.org, openjdk.org/jeps, peps.python.org, freely available ISO/IEC standards, The Open Group (POSIX) |
| ★★★ | **Peer-reviewed / seminal papers** (open copy) | arXiv, usenix.org (open access), open-access ACM/IEEE papers, VLDB proceedings, author pages (e.g. lamport.azurewebsites.net), EWD archive (cs.utexas.edu/~EWD) |
| ★★ | **Reference open-source code** — mature, widely deployed, readable | PostgreSQL, SQLite, Linux, FreeBSD, OpenJDK, CPython, Apache projects, Git — source + design docs + mailing-list rationale |
| ★★ | **Classic open books** | SICP (MIT Press open edition), *The Architecture of Open Source Applications* (aosabook.org), *OSTEP* (ostep.org), Lamport's *Specifying Systems* |
| ★ | **Practitioner essays** with a primary-source trail | only to point to a ★★★/★★ source, never as the evidence itself |

Discovery tools (find the source, don't cite them): dblp, Semantic Scholar, OpenAlex,
Google Scholar, Software Heritage, Wikipedia's reference lists.

Excluded: Medium/dev.to/SEO listicles, vendor marketing & "whitepapers", AI-generated
summaries, Stack Overflow answers as evidence, conference talks without a written paper,
anything behind a paywall.

## Protocol

### 1. Restate the problem in timeless terms

Strip framework, vendor and version: "dedupe Kafka messages in Spring" → *idempotent
consumption over at-least-once delivery*. List the **old names** of the concept across
eras and fields (e.g. saga — Garcia-Molina & Salem 1987; write-ahead logging; leases —
Gray & Cheriton 1989; backpressure; capability-based security). Those words are the
search keys; modern buzzwords usually aren't.

Show this restatement to the user in two lines before searching — a wrong framing wastes
every search after it.

### 2. Search, tier by tier

- Standards first: `site:rfc-editor.org`, `site:w3.org/TR`, … — a spec settles what an
  essay only argues.
- Papers: `site:arxiv.org`, `site:usenix.org`, `filetype:pdf "<old name>"`, the
  concept + "survey".
- **Chase citations backward**: from a good recent paper, follow its references to the
  origin; from the origin, check who built on it (Semantic Scholar / OpenAlex) for
  known refutations or refinements.
- Reference code: how PostgreSQL/SQLite/Linux/… implement it, *and* the commit message,
  design doc or mailing-list thread explaining why.

Aim for **3–7 strong sources**, not 30 weak ones. Stop when new searches only return
what's already found.

### 3. Read the source, not its summary

Fetch each one; extract the claim, the conditions it holds under, the trade-off the
authors themselves state, and the exact location (section, page, `file:line` at a tagged
release or commit hash for code).

### 4. Lindy screen

A source is a **pillar** when at least one holds:

- ≥ ~10 years old *and* still cited or implemented today
- standardised (RFC on standards track, W3C Recommendation, accepted PEP/JEP, …)
- ≥ 2 independent mature implementations of the idea

Anything else is **recent**: allowed only if it builds explicitly on a pillar, and
flagged as such. Popularity, stars, or "everyone uses it now" never make a pillar.
Note also what an old source *got wrong* or what the field has since retracted: the
lineage includes its corrections.

### 5. Synthesize

Map what was found onto the user's problem: which pattern fits, under which assumptions,
what it costs, which known failure modes come with it. Separate what the sources say from
your own inference, and say where the user's context breaks an assumption of the source.

## Report (inline)

```
Problem (timeless): <one sentence> — also known as: <old names>

Lineage (oldest → newest)
  1975  <Author>, <Title> — <one-line idea>                  [pillar] <URL> §x
  1987  <Author>, <Title> — <refinement>                     [pillar] <URL> p.y
  2014  <RFC/spec>        — <standardised form>              [pillar] <URL> §z
  2021  <Author>, <Title> — <recent variant, builds on 1987> [recent] <URL>

Patterns
  | Pattern | Holds when | Costs / trade-off | Known failure mode | Source |

Reference implementations
  <project> <tag/commit> <path:line> — <how they do it, why (link to rationale)>

Applying it here: <recommendation + the assumption to check in our context>
Not found / not verified: <gaps, references recalled but not fetched, paywalled-only>
Next: /thought-experiment on <chosen pattern> against our case
```

## Don't

- Don't read local files or code to find prior art — online only.
- Don't cite anything not fetched in this session, nor anything paywalled.
- Don't present a recent trend as established because it's popular.
- Don't stop at secondary sources: follow them to the primary one or drop them.
- Don't copy code verbatim into the user's project from a source with an incompatible
  license — cite it, explain the idea, and name the license.
- Don't conclude "best practice" without saying under which conditions the source
  claims it holds.
