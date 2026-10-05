---
name: thought-experiment
description: >-
  Run a thought experiment (Gedankenexperiment) on a code hypothesis: simulate a concrete
  situation on paper — no execution, or only a separate, opt-in dry run — with the sole
  aim of REFUTING the hypothesis. Never "confirms": a hypothesis that survives is only
  corroborated. Rooted in Galileo, Einstein, Mach, Popper, Chamberlin/Platt. Use to test a
  bug theory, a fix, a concurrency/ordering assumption, an invariant, a migration or
  design choice before (or instead of) running anything. Manual only: /thought-experiment.
disable-model-invocation: true
metadata:
  author: Olivier G
---

# thought-experiment

A thought experiment is an experiment run in the head, on a world specified precisely
enough that the outcome is *forced* by the premises. Galileo never needed to drop
anything from Pisa: tying a heavy and a light stone together was enough to make
Aristotle's law contradict itself. Applied to code, the "world" is the actual source,
config and data, and the "laws" are the language, the libraries and the runtime.

The aim is **asymmetric** (Popper): one sound counterexample refutes a hypothesis; no
number of survived scenarios proves it. So the experiment is designed to **break** the
hypothesis, never to illustrate it. Survival means *corroborated, so far, against these
attacks* — and the report says exactly which attacks.

> "The first principle is that you must not fool yourself — and you are the easiest
> person to fool." — Feynman, *Cargo Cult Science* (1974)

## The lineage — and what each move becomes in code

| Origin | Move | In code |
|--------|------|---------|
| Galileo, falling bodies (*Discorsi*, 1638) | **Reductio**: combine two consequences of H until they contradict | Apply H to two parts, then to their composition (A, B, then A∘B / A+B in one tx / batch of 1 vs N) — does H predict two outcomes for the same thing? |
| Galileo's ship (*Dialogo*, 1632) | **Invariance**: an observer inside can't tell if the ship moves | A retry vs a first call, a restart vs a fresh start, replica A vs B: if the code sees the same inputs and state, H must predict the same outcome — or H leans on a difference the code can't see |
| Stevin's chain (1586) | Posit something known impossible (perpetual motion) and derive | "If this were true, we could get X for free" (unbounded throughput, exclusivity without a lock, exactly-once on an at-least-once transport without dedup) → H is wrong |
| Einstein, train & lightning (*Relativity*, 1917) | **Operationalize**: a concept means what you could measure | Replace vague words ("after", "atomic", "consistent", "fresh") with what the code can observe: which clock, which commit, which read sees which write |
| Einstein's elevator (equivalence principle, 1907) | **Equivalence**: indistinguishable causes ⇒ same effects | Two code paths that look identical to the callee (mock vs real, cache hit vs miss, sync vs async) — prove they really are, or find the difference |
| Maxwell's demon (1867) | An **agent** with perfect knowledge and timing | The scheduler/network/user as a demon: choose the worst interleaving, the worst moment to crash, the worst message reorder or duplicate |
| Schrödinger's cat (1935) | **Amplify** a micro-claim to a macro absurdity | Scale it: 1 → 10⁶ rows, 1 → 1000 threads, 1 day → 2 years of data, `int` → overflow, one tenant → all |
| Mach (1897) | **Vary the parameters continuously**, look at the limits | Push each variable to 0, 1, max, negative, null, empty, duplicate, NaN, DST boundary, leap day — watch where the outcome flips |
| Chamberlin (1890), Platt (1964) | **Multiple working hypotheses**, crucial experiment | Never test H alone: list the rivals, pick the scenario where they predict *different* outcomes |
| Popper (*LSD*, appendix *xi) | **Critical, not apologetic use** | Every simplification in an attacking scenario must be one H's defender would grant — otherwise it refutes a straw man. And when a scenario breaks H, don't rescue it with an ad hoc auxiliary ("but nobody would call it that way") |
| Klein's premortem (2007) | **Prospective hindsight** | "It's in prod and it failed. Write the incident report." Then check each cause |

Norton's caveat: a thought experiment is "a (possibly disguised) argument" — only as good
as its premises. The vivid story adds no logical force; every premise must be traceable.

## Protocol

### 1. State H so it can be wrong

One sentence, with its **prohibited outcome**: "H: `refresh()` can't produce two active
tokens for one user — so two rows with `active=true` must never coexist." If nothing
observable could contradict H, it's not a hypothesis yet — sharpen it (Einstein: what
would you measure?) before going on.

### 2. List the rivals

2–4 alternative explanations or designs (Chamberlin). For each, what it predicts
differently. Prefer scenarios where they diverge: one where all agree can't tell them apart.

### 3. Fix the world

Premises, each one sourced, none imagined:

- code: the exact version — read it, cite `file:line`; never simulate from memory of
  what the code "probably" does
- runtime semantics: isolation level, memory model, framework defaults, library
  behavior — check the doc or the library source when it matters (folk intuition about
  a library is the commonest false premise)
- config, data shape, volumes, deployment topology (replicas, partitions, clocks)
- **ceteris paribus**: say explicitly what is held fixed and what is assumed

Unknown premise → mark it `ASSUMED` and keep it visible; it bounds the verdict.

### 4. Build scenarios to break H

Pick from the lineage table the moves most likely to hurt *this* H: reductio,
invariance, limits, the demon's interleaving, amplification, premortem. Prefer the
scenario H's author would find most uncomfortable — but simplify only in ways they would
grant (Popper), or the refutation hits a straw man. Write each one as concrete inputs and
initial state, not as a category ("concurrent access" is not a scenario; "T1 reads v=3 at
L42, T2 commits v=4, T1 writes v=4 at L57" is).

### 5. Run it — step by step, on paper

Trace with an explicit state table; one row per step, each step justified by a line of
code or a documented semantics:

```
step | actor | location         | action              | state after
1    | T1    | TokenSvc.java:42 | SELECT … FOR UPDATE | lock(user=7)=T1
2    | T2    | TokenSvc.java:42 | SELECT … FOR UPDATE | T2 blocked
…
```

No "obviously" step: the jump you skip is where the bug lives. When you can't determine
the next state from the premises, stop and say so — that's a finding, not a gap to fill
with a plausible guess.

### 6. Verdict — three outcomes only

- **REFUTED** — a counterexample: the exact inputs/interleaving, the step where the
  prohibited outcome appears. Reproducible from the trace alone.
- **CORROBORATED (provisional)** — every scenario tried failed to break H. List them, list
  the `ASSUMED` premises, and name the attacks **not** tried. Never write "confirmed",
  "proven", "guaranteed", "safe".
- **UNDECIDABLE ON PAPER** — the outcome hinges on a premise that reading can't settle
  (real timing, an opaque library, actual data). → propose a crucial experiment (below).

### 7. After a refutation

Don't patch H to survive the counterexample (Popper's "apologetic use"; Lakatos's ad hoc
auxiliaries in the protective belt). State a new H′ explicitly, say what it gave up, and
run it through the protocol again — including the scenario that killed H.

## Crucial experiment — the dry run, separately

Only when step 6 says undecidable, and only **after the user agrees**. It's a distinct
step, never mixed with the thought experiment.

- **Write the prediction first** — what each rival predicts — then run. A result read
  without a prior prediction can be made to fit anything.
- Smallest thing that discriminates the rivals: a unit test, a REPL expression, an
  `EXPLAIN`, a `--dry-run`, a transaction rolled back, two threads in a scratch file.
- Read-only / sandboxed / local by default. Nothing that touches shared or prod state.
- One result decides between rivals; it never upgrades a survivor to "proven".

## Report

```
H: <one sentence> — prohibited: <observable>
Rivals: H2 <…>, H3 <…>
World: <commit/files>, ASSUMED: <premises not verified>
Scenarios:
  1. Demon interleaving T1/T2 at L42–57 → H survives (row lock held)
  2. Limit: user with 0 tokens → H survives
  3. Invariance: retry after timeout → REFUTED at step 6 (second INSERT, no unique key)
Verdict: REFUTED — counterexample: <inputs + trace step>
Not tried: multi-region clock skew, manual SQL fixes
Next: H′ <…> | crucial experiment: <proposal, awaiting go>
```

## Don't

- Don't execute anything during the thought experiment itself. Reading code, docs,
  library sources: yes. Running: only the separate dry run, on consent.
- Don't build the scenario from the conclusion (scenarios chosen because H passes them).
- Don't stop at the first survived scenario — survival is cheap, refutation is the goal.
- Don't let a vivid narrative stand in for a premise: if it isn't in the code or the doc,
  it's `ASSUMED`.
- Don't conclude beyond the world you fixed: "refuted under READ COMMITTED" is not
  "refuted".
