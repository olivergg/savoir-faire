---
name: guided-walkthrough
description: >-
  Explain something complex ONE step at a time, pausing after each step for the user to
  validate before continuing. Use when the user wants to *understand* a change, an
  algorithm, a diagnosis, a design decision, or a piece of code — especially after you've
  just built or investigated it, or before you implement it. Triggers: "explique pas à pas",
  "explique étape par étape avec pause", "explique avant de faire", "guide-moi",
  "explain step by step", "walk me through it", "one step at a time", "let me validate as
  you go", "je veux comprendre en détail".
metadata:
  author: Olivier G
---

# guided-walkthrough

Deliver a complex explanation as a **sequence of small steps, one message per step**, each
ending with a checkpoint. The user drives the pace. The point is *understanding transfer*,
not coverage — so this is deliberately multi-turn and slower than a normal answer. Worth it
when the user asks for it; not for routine status updates. When asked for, it overrides any terse/token-saving mode
active in the session.

## 1. Anchor on a concrete before → after

Before step 1, establish the artifact the whole walkthrough hangs on: the actual code /
query / plan / number **as it was**, not the solution. Start from "before" and move forward
to "after" — never open with the fix. If there's no natural artifact, pick the smallest
concrete example that exhibits the thing.

## 2. Decompose into steps — one idea each

Each step teaches **exactly one thing**. Not "here are the 3 causes AND the fix AND the
caveat". If a step needs two ideas, it's two steps.

Default narrative order (adapt as needed):

1. what it does / what it's for
2. the symptom — measured, with numbers
3. the diagnosis — read the evidence (the plan, the profile, the diff)
4. why it behaves that way — the mechanism / root cause
5. the fix — concretely, what changes (show before/after side by side)
6. why the fix works — map each change to the cause it removes
7. the catch — the condition, the trade-off, why it isn't always safe
8. how it was validated

## 3. The pause protocol (the core discipline)

End **every** step with, in this order:

- a **validation question** that restates the step's claim in one sentence and asks the user
  to confirm it landed ("clair que … ?")
- a **one-line preview** of the next step + "je continue ?" / "continue?"

Then **stop**. Do **not** put step N+1 in the same message. Wait for the user's reply.

If the user says "oui" / "continue" → emit step N+1 the same way.
If the user asks a question → answer it, re-ask the checkpoint, do not advance.

## 4. On "je comprends pas N" / "I don't get N"

Do **not** advance. Re-explain step N *differently*:

- a concrete worked example with real values
- an analogy
- break it into 2-3 sub-steps

Then re-ask the checkpoint for N. Only move on once it lands.

## 5. Close with a compact recap

After the last step: a small table, one row per step (`étape | une phrase`). This is the
takeaway artifact — keep it dense and skimmable.

## Anti-patterns

- Dumping several steps because "they're short" — the pause *is* the feature.
- Advancing on silence or on a mid-turn message that isn't a clear "yes".
- Opening with the solution then explaining backwards.
- A step that introduces a term without grounding it (define via example, not definition).
- Padding steps with caveats that belong in a later step.

## Skeleton (fill per topic)

```
## Étape 1 — <ce que ça fait>

<le "avant", concret : le code / la requête / le chiffre>

**Points à retenir :** <1-3 puces>

---
**Validation :** <reformulation de la claim en 1 phrase> — clair ?
Je continue vers l'étape 2 (<une ligne>) ?
```
