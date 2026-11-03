---
name: how-i-prompt
description: Use this skill when the user wants the timeline of what a person actually typed during a Claude Code session — every prompt verbatim (typed prompts, slash commands, mid-turn messages, multiple-choice answers, refusals with feedback), each followed by a one-line summary of what the agent did — to study how people prompt, debrief a workshop, or review a session. Writes Markdown and JSON. Also triggers for: comment j'ai prompté, mes prompts, récap des prompts, timeline des prompts, historique de la session, how did I prompt, prompt history, session timeline.
metadata:
  author: Olivier G
---

# how-i-prompt

What matters here is **how the person prompted**: the exact words, in order, and the decisions
they made in answer to questions. The agent's replies are reduced to one line each.

A script does all the extraction (deterministic, local, read-only on `~/.claude/projects/`). You
only write the one-line summaries.

## Steps

1. Extract the session. Default: the most recent session of the current directory.
   ```bash
   python3 scripts/how_i_prompt.py extract -o how-i-prompt.json
   ```
   - Another session: `--session <id or id prefix or .jsonl path>`.
   - Another project: `--project <dir>` (its most recent session).
2. Fill `resume` for every turn in the JSON: **one line**, in the language of the session, saying
   what the agent did in answer — the action and its outcome, not the topic. Use `tools`, `files`
   and `reply_excerpt`. Examples: « Lance un agent qui compte l'usage des skills, puis pose 4 QCM. »,
   « Corrige le titre de la slide 3 et vérifie sur capture. » Never paraphrase the prompt itself.
   For a `réponse QCM` turn, say what the agent did *with those answers* (built, decided, asked
   next). The question being answered was asked in the previous turn; an `AskUserQuestion` in
   this turn's `tools` is the *next* dialog, not this one. For the last turn of a session still in
   progress, write « tour en cours » if the excerpt shows no outcome yet.
3. Render the Markdown:
   ```bash
   python3 scripts/how_i_prompt.py render how-i-prompt.json -o how-i-prompt.md
   ```
4. Hand back both paths. Add three or four observations only if the user asked for an analysis
   (prompt length, how often they corrected course, answers taken as recommended vs. chosen).

## What counts as a human turn

| Kind | Source in the transcript |
|---|---|
| `prompt` | a typed user message |
| `commande` | a slash command, rendered `/name args` |
| `en cours de tour` | a message typed while the agent was working |
| `réponse QCM` | the answers to an AskUserQuestion dialog, `question → answer` |
| `réponse QCM partielle` | a dialog closed to clarify, with the answers given so far |
| `refus avec consigne` | a refused tool call with the person's instruction |

Ignored: harness reminders, skill bodies, tool results, subagent transcripts, interruptions.

## Rules

- Prompts stay **verbatim**, typos included: they are the point. The only edits are masking.
- Masked by the script: tokens and API keys, `password=…`-style values, JWTs, emails, home paths
  (`/Users/<name>` → `~`). Don't add or remove anything else.
- Nothing leaves the machine. Don't paste the output anywhere unless the user says so.

## Changing the script

Run `python3 evals/test_how_i_prompt.py` before and after. `evals/session.jsonl` holds one record
of every kind (human turns, harness noise, subagent, secrets); add a record when a new kind shows up.
