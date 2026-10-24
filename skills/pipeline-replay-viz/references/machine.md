# The machine (animated replay)

Goal: make the current functioning understandable by watching real records travel through
the pipeline, stage by stage, and seeing exactly where BEFORE and AFTER diverge.

## Stations
One station per real stage, named with its real component name and a plain-language
caption. Typical chain:
1. **Source** — emits the real record (card: type/trigger, key fields, source session id).
2. **Ingestor / stream processor** — splits the record into messages per topic; shows each
   transformation (mapping, unit conversion) and each **filter** as a gate that remembers
   what it last saw ("seen: 4 % at 05:57:18") and drops a message visibly (✂, falling away).
3. **Topics / queues** — belts or pipes, one per topic, with live counts.
4. **Connector / writer** — merges messages into a row (e.g. upsert on key + timestamp:
   cells fill as messages with the same key arrive).
5. **Storage** — rows appear with only the columns received.
6. **Service logic** — reads rows in order; lamps for its state (open/closed, active),
   the running computed values, and **the rule that fired** for each row, with its reason.
7. **Result** — final objects vs the source's own session on a mini timeline, then cards.

## Fidelity (non-negotiable)
- Intermediate messages are **recomputed deterministically from the real inputs** with the
  rules of each run, then the resulting rows are **compared with the real stored rows** of
  that run for the excerpt. Show the result on the page ("faithful to real data ✓ 29/29")
  or list mismatches. Replay in arrival order: stateful filters depend on it.
- Service logic: either call the real code offline, or port it branch by branch and
  validate the port on the whole period against the real final objects (report n/N). The
  final cards always show the real objects.
- Everything simplified for teaching is stated on the page (e.g. "the service reads the
  table at query time; here it reads rows as they arrive").

## Timeline & controls
- Deterministic, seekable timeline built from the excerpt's records (one slot per record,
  idle gaps collapsed and labelled "⏩ 2 h without records").
- Play/pause, step back/forward, speeds ×¼ ×½ ×1 ×10 ×60, scrubber with ticks for drops,
  opens/closes, divergences and numbered notes.
- BEFORE / AFTER / both (two machines in sync, ⚑ where the service decides differently).
- Live counters: records in, messages per topic, dropped by filters, rows written, objects.
- Click any record / message / row / object / narration line → inspector with exact content.
- Intro overlay "how to read the machine", legend, light/dark, reduced motion → stepwise
  playback. Keyboard: space, ←/→, mode keys, excerpt number keys.

## Excerpts
3–5 short windows, each showing one mechanism, with a "what to watch" caption and timed
notes for BEFORE and AFTER (facts in notes checked against the data).
