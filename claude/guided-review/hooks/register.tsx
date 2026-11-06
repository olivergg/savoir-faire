import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { Explanation } from '../types'

const PANE = 'guided-review'
const TOOL = 'mcp__guided-review__show_explanation'
const explanation = atom({ plugin: 'guided-review', key: 'explanation' } as const, null as Explanation | null, {
  shape: 'explanation-2',
})

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.tool.register({
      name: 'show_explanation',
      description:
        'Guided code review: show the explanation of the file currently under review in the side pane, ' +
        'instead of writing it in the reply. The reply holds only the diff, pasted as a ```diff fenced block ' +
        '(full file content in a fenced block with its language for a new file): a Bash git diff output is ' +
        'folded in the transcript, the person does not see it.',
      inputSchema: {
        type: 'object',
        properties: {
          file: { type: 'string', description: 'Repo-relative path of the file' },
          position: { type: 'string', description: 'Position in the review, e.g. "3/26"' },
          why: {
            type: 'string',
            description:
              'Markdown, short: why this change exists. The problem it answers (pentest finding, bug, ticket need), ' +
              'where it sits in the branch story, what it enables or depends on in earlier/later files',
          },
          what: { type: 'string', description: 'Markdown: what the diff changes, call sites, points to check' },
        },
        required: ['file', 'position', 'why', 'what'],
      },
      isDeferred: false,
    })
    await $.command.register({ name: 'guided-review', description: 'Reopen the guided review pane' })

    return next(e)
  })

  on('command.run', { command: 'guided-review' }, async $ => {
    await $.ui.open({ id: PANE, title: 'Review' })

    return { text: 'Guided review pane opened.' }
  })

  on('tool.call', { tool: TOOL }, async ($, e) => {
    const { file, position, why, what } = e as unknown as Explanation
    await update($, explanation, () => ({ file, position, why, what }))
    const opened = await $.ui.open({ id: PANE, title: 'Review' })
    const shown = opened.isPlaced ? 'shown in the side pane' : `pane not drawn (${opened.reason}), give it in the reply`

    return { result: `Explanation of ${file} ${shown}.` }
  })

  // Navigation band above the prompt: each button sends the words the person would type, so Claude stays the driver
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const shown = await read($, explanation)
    if (!shown || e.props.hasSurvey) return next(e)
    const { Box, Button, Text } = $.ui.resolve(e)
    const send = (text: string) => () => void $.prompt.submit({ text })

    return (
      <Box gap={2}>
        <Text dimColor>
          📄 {shown.position} · {shown.file.slice(shown.file.lastIndexOf('/') + 1)}
        </Text>
        <Button key="prev" label="◀ Précédent" onPress={send('précédent')} />
        <Button key="next" label="Suivant ▶" variant="primary" onPress={send('suivant')} />
        <Button key="diff" label="🔁 Diff" onPress={send('réaffiche le diff du fichier courant')} />
      </Box>
    )
  })

  // The call's row would print the whole why/what already shown in the pane: one line instead (ctrl+o shows all).
  on('ui.render', { component: 'ToolUse' }, async ($, e, next) => {
    if (e.props.tool !== TOOL || e.props.isExpanded) return next(e)
    const { Text } = $.ui.resolve(e)
    const { file = '', position = '' } = (e.props.input ?? {}) as Partial<Explanation>

    return (
      <Text dimColor>
        📄 {position} · {file.slice(file.lastIndexOf('/') + 1)} → pane
      </Text>
    )
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Markdown } = $.ui.resolve(e)
    const shown = await read($, explanation)
    if (!shown) return <Text dimColor>No file under review yet.</Text>

    const slash = shown.file.lastIndexOf('/')
    const [n = 0, total = 0] = shown.position.split('/').map(Number)
    // Bar sized to the pane, leaving room for the "n/total" label.
    const width = Math.max(10, e.props.bodyColumns - shown.position.length - 2)
    const done = total > 0 ? Math.round((width * n) / total) : 0

    return (
      <Box flexDirection="column" gap={1}>
        <Box borderStyle="round" borderColor="claude" paddingX={1} flexDirection="column">
          <Text bold color="claude">
            📄 {shown.file.slice(slash + 1)}
          </Text>
          {slash > 0 && <Text dimColor>{shown.file.slice(0, slash)}</Text>}
        </Box>
        <Text>
          <Text color="success">{'█'.repeat(done)}</Text>
          <Text color="inactive">{'░'.repeat(width - done)}</Text> <Text bold>{shown.position}</Text>
        </Text>
        <Text bold color="warning">
          🧭 Pourquoi
        </Text>
        <Markdown text={shown.why} />
        <Text bold color="suggestion">
          💡 Quoi
        </Text>
        <Markdown text={shown.what} />
      </Box>
    )
  })
}
