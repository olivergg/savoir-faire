# guided-review

Claude Code mod for a file-by-file code review at your own pace, driven by a review skill such as
`guided-code-review`. Claude prints each file's colored diff in the transcript; this mod shows the explanation of
that file beside it.

- **Side pane**: file name and path, a progress bar (`n/total`), then **🧭 Pourquoi** (the problem the change answers,
  its place in the branch story) and **💡 Quoi** (what the diff changes, points to check).
- **Band above the prompt**: `◀ Précédent`, `Suivant ▶`, `🔁 Diff` buttons, each sending that request in your place.
- **Compact tool row**: the `show_explanation` call shows as one line in the transcript (ctrl+o for the full call).
- `/guided-review` reopens the pane.

Claude fills the pane through the tool `mcp__guided-review__show_explanation` (`file`, `position`, `why`, `what`).
CLI only; elsewhere the review skill falls back to plain text.

## Install

```
claude plugin marketplace add olivergg/savoir-faire
claude plugin install guided-review@savoir-faire
```
