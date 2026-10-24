# Before/after explorer

Goal: let a developer and a non-developer see, entity by entity and day by day, how source
records become stored rows and final objects in each run, and where BEFORE and AFTER
diverge from the source's truth.

## Inputs (all files, no live connection)
- Raw captured records per entity/day.
- Per run: stored rows (one line per row, all columns the stage writes), final objects
  produced by the real service code, a meta file (label, branches, commits).
- The comparator's verdicts (computed by the generator, same thresholds as the analysis).

## Layout
1. **Header**: run mode switch BEFORE / AFTER / side by side, theme toggle, "Explanations".
2. **Entity chips** with a mini KPI (total, number of divergences before → after).
3. **Day strip**: one cell per day with a sparkline of the main measure, counts, ⚠ when a
   verdict fails, ≠ when BEFORE and AFTER differ.
4. **Day view, one shared x-axis** (zoom/pan linked across lanes):
   - source lanes: main measure curve (break the line over idle gaps — no line across a
     period without records), secondary measure, discrete events (▲▽●○), the source's own
     session/transaction id bands;
   - BEFORE block, then AFTER block, each: stored-row markers per column (filled = true,
     hollow = false, tooltip = full row) and final objects as bars;
   - the source's session drawn as a dashed outline inside each block so a cut is visible.
5. **Comparison table**: one line per source session → matched object in BEFORE and AFTER
   (times, values, totals, type) + verdict chip and one-line reason; hover highlights it on
   the chart, click zooms to it.
6. **Period summary**: totals source / BEFORE / AFTER on one shared axis, counts,
   divergences per entity and overall (animated counters/bars).
7. **Explanations drawer**: the chain as a diagram with what BEFORE and AFTER do at each
   stage, what changed, known remaining limits, how to read verdicts, glossary.

## Interaction
- Tooltips everywhere with the exact record / row / object (raw line included).
- Keyboard: ←/→ day, ↑/↓ entity, mode keys, +/−/0 zoom, Esc. URL hash keeps entity/day/mode.
- Animated transitions that explain: switching BEFORE↔AFTER morphs each bar from its
  BEFORE extent to its AFTER extent (pair by overlap; unmatched bars fade).
- Empty states with a reason (e.g. "the source sent almost nothing this period").

## Visual rules
Validated categorical palette (source / BEFORE / AFTER = three distinct hues, fixed),
one y-axis per chart (never dual axes), legends always present, text in text colors,
light + dark selected (not auto-inverted), `prefers-reduced-motion` respected.
