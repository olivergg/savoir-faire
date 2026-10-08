---
name: triple-check
description: >-
  Re-verify, from scratch and against independent sources, everything just claimed or
  changed — findings, analyses, diffs, plans, procedures — before the user acts on it
  (commit, push, post, delete, apply, share). Each claim gets a verification level; no
  blanket "all good". Chains to /second-pass for code and /thought-experiment for what
  can't be run. Manual only: /triple-check.
disable-model-invocation: true
metadata:
  author: Olivier G
---

# triple-check

"Triple check" means: **the previous pass is not evidence.** Re-derive each claim as if
someone else had made it, from sources that don't share its blind spots. The user asks
because a confident first answer has been wrong before — so a triple check that just
restates the first answer with ✅ is worse than none.

Seen in practice: "triple check again" found 3 leftovers because the earlier passes were
spot-checks, never a repo-wide grep. "Tout a été triple check ?" got the right answer
only when it was an honest per-claim table, some rows marked single-source.

## 1. Scope — what exactly is under check

Name it in one line before starting; infer from the request:

| Request shape | Object |
|---------------|--------|
| "triple check tout" after code work | the whole change **since the branch start point** (`git merge-base`), not `master..HEAD`, plus uncommitted files |
| "triple check ce finding / tes affirmations / la source" | each factual claim made so far |
| "triple check le plan / la procédure" | every step, its order, its preconditions and its undo |
| "triple check avant de push/supprimer/poster" | the action itself and what it touches |
| "triple check X" (named thing) | only X — don't widen into a full review |

## 2. Inventory the claims

List every claim the conclusion rests on — explicit or implicit ("nothing else uses
this", "compiles", "same users/folders as before", "default is Y", "branch is gone").
A claim not in the list won't get checked; that's where the miss hides.

## 3. Verify each claim through ≥2 independent sources

Prefer the strongest available; reading the same file twice is one source.

| Strength | Source |
|----------|--------|
| ★★★ | **Execution**: compile, test, `--dry-run`, REPL/nREPL repro, query the real (read-only) system, `curl` the endpoint |
| ★★★ | **Exhaustive search**: repo-wide grep incl. docs/config/scripts, *and* sibling repos that may consume it (front ↔ back, infra, CI, k8s) |
| ★★ | **Primary source**: the library/tool source code, official docs/spec, the actual cluster/infra config — never memory or forum posts |
| ★★ | **Data**: counts on the full set, not a sample; check recency (mtime, last commit) before declaring something unused |
| ★ | **Prior art**: how others do it (GitHub code search, upstream projects) — supports a design, never proves a fact |
| ★ | **Simulation on paper**: trace execution step by step (escaping, relative paths, ordering) → `/thought-experiment` |

Execution and anything touching shared state: read-only by default; if a check needs a
write or apply, say so and ask.

Per kind of object, don't skip:

- **Code change**: nominal behavior unchanged (trace the main path before/after); no
  logic change hidden in a refactor; callers of every changed signature; dangling
  references/imports; edge cases (null, empty, 0/1/max, concurrent, retry); build + tests
  actually run. Then `/second-pass` for leftovers and compactness.
- **Finding / diagnosis**: reproduce it; try to refute it (rival explanation that fits
  the same evidence); separate "observed" from "inferred".
- **Plan / procedure**: each command dry-run or read against the doc; order and
  preconditions; reversibility of each step; accounts/remotes/targets are the right ones.
- **Destructive or outward action**: re-verify the target state *now* (it may have
  changed since the analysis), then stop for an explicit go.

## 4. Report

Lead with what changed vs the previous answer — that's the point of the exercise.

```
Changed since last pass: <fixed/retracted/new findings — or "nothing">
| Claim | Verified by | Level |
|-------|-------------|-------|
| X no longer referenced | repo-wide grep + ocean-front grep | ✅ 2 sources |
| default timeout = 30s | lib source L123 + doc | ✅ 2 sources |
| no prod impact | reasoning only | ⚠️ 1 source — <how to verify> |
Not checked: <what and why>
```

- Retract plainly what turned out wrong; don't soften it into "nuance".
- Words: "verified by …", "not verified". Never "100% sûr", "guaranteed", "tout tient".
- Doubts the user must settle → ask as multiple-choice, don't guess.

## 5. Then — only if the request said so

"triple check **et go / et oui / puis commit**": proceed only if the check came back
clean; any fix or retraction → report and wait. Before push/post/delete/apply, ask one
last time unless the user already gave the go for that exact action.

## Don't

- Don't re-read your earlier answer and call it verified.
- Don't sample when you can count; don't spot-check when you can grep everything.
- Don't widen a named check into a full review, or narrow "tout" to the last edit.
- Don't run anything that writes to shared/prod state as "verification".
