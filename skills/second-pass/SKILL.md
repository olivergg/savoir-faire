---
name: second-pass
description: >-
  Re-read code you just produced and cut it down — delete, reuse, hoist, generalize,
  compact — at strictly equivalent behavior, then look for the same win in the
  neighbouring code. Run it by default before proposing a commit, and on request.
  TRIGGER when: simplifie, simplifier, compacte, compresse, factorise, hoiste, inline,
  mutualise, réutilise, généralise, allège, réduis le code, moins de méthodes,
  trop verbeux, nettoyage habituel, clean leftovers, prends du recul, remets en question,
  relis ce qu'on a fait, à fonctionnalité équivalente, minimize the diff, DRY,
  over-engineered, simplify, compact it, compress the code, refactor, deduplicate,
  reuse existing, is there something existing we can reuse, second pass, triple check
  the code, quelque chose qu'on a raté.
metadata:
  author: Olivier G
---

# second-pass

A first draft is a *proposal*, not a result. An LLM writing code optimizes for "it works
and it's explained", which systematically overshoots: a helper that duplicates an existing
one, a record where a map would do, a comment restating the line under it, an abstraction
for a single caller, a parameter nobody passes. None of it is wrong — all of it is
**unearned**. The second pass is where the actual design happens.

Two things make this different from "tidy the code":

- **Economy is measured in characters and concepts, not lines.** Fewer, denser,
  idiomatic constructs beat more lines of scaffolding — up to the point where a reader
  slows down. Readability is the hard constraint, compactness the objective.
- **A simplification is almost always sitting next to the one you were asked about.**
  The duplicate you just removed has a sibling two files over. Look there before
  reporting done.

## Discipline

- **Behavior stays strictly identical.** No "while I was in there" fix, no scope
  creep, no API change unless asked. If you spot a real bug, report it — don't fold it
  into the cleanup.
- **Prove it**: run the tests / linter / formatter before and after. No suite → say so
  explicitly, and keep the diff small enough to eyeball.
- **Present the reasoning, not just the diff**: one line per cut, saying *why* it was
  unearned. That's what lets the user push back.
- Compression that costs a re-read is a loss. Don't golf, don't chain six
  transformations into one expression, don't drop a name that carried meaning.

## Passes, in this order

Order matters: deleted code needs no simplifying, and reusing something existing beats
generalizing your own.

1. **Delete.** Dead code, unused params/imports/vars, a flag with one value, defensive
   checks for impossible states, tests asserting the framework, TODOs already done.
   Also: anything **never asked for** — an extra output, a config knob, a fallback for a
   case that can't happen. Question the requirement, not just the implementation.
2. **Reuse.** Does this already exist — in this file, this module, a shared util, the
   framework, the stdlib? Search before keeping any new helper. A helper with one caller
   that wraps three lines is usually not a helper.
3. **Hoist / generalize** — but only on real, *present* duplication (2-3 occurrences), not
   anticipated. Push a piece up to the layer that owns it (shared module, SDK, base
   class) when more than one caller genuinely needs it. One caller = leave it inline.
4. **Compact.** Idioms over scaffolding, in the language's own grain: threading macros,
   destructuring, `cond->` (Clojure); `var`, records, switch expressions, streams (Java);
   comprehensions, unpacking (Python). Collapse a lone intermediate variable, merge
   near-identical branches and near-duplicate tests, prefer data over code (a map *is* a
   function of its key).
5. **Name.** A precise name deletes a comment. Shorten what's obvious from context, spell
   out what isn't, drop type/prefix noise.
6. **Comments and docs, last** — once the code is final. Keep only the *why* that the code
   can't state: non-obvious logic, a constraint, a trap. Delete anything restating the
   signature or narrating the next line. See `concise-output` for the writing style.

## Then widen

Before reporting: re-read the **full diff** of the change, and the code immediately around
it. Ask explicitly — "the cut I just made, does it apply anywhere else here?" A pattern
worth extracting usually has 2-3 more instances one file over, and those are the ones the
user will find later and be annoyed about.

## Report

A few lines, grouped by pass, each naming the cut and why it wasn't earned:

```
- Deleted: `:retries` opt — every caller passes the default.
- Reused: dropped `formatStamp`, `DateFmt.iso()` already does it.
- Hoisted: the 3 identical probe blocks → one `reachable?` (tunnel.clj).
- Compacted: 4 cond branches → one map lookup.
- Kept on purpose: the two similar tests — same shape, different contract.
Tests: 236/236 green, formatter clean. Behavior unchanged.
```

State what you deliberately **didn't** touch and why — an untouched duplication with a
reason is a finding, not an omission.

## Don't

- Don't run it on code the user is still shaping, mid-discussion — wait for a working state.
- Don't touch generated, vendored or third-party files.
- Don't rewrite a file wholesale to make it "cleaner": cuts must stay reviewable.
- Don't chase a metric. "Fewer lines" achieved by cramming is a regression.
