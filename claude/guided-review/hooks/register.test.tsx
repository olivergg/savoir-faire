import { expect, test } from 'claude-code/testing'

const PANE = {
  plugin: 'guided-review',
  component: 'Pane',
  requestId: 'guided-review',
  props: {
    title: 'Review',
    isFocused: false,
    bodyColumns: 60,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 30 },
    view: {},
  },
} as const

test('show_explanation fills the pane', async ($, on) => {
  on('tool.register', () => ({ value: { tool: 'mcp__guided-review__show_explanation' } }))
  on('command.register', () => ({ value: { command: 'guided-review' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))

  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  const call = await $.tool.call({
    tool: 'mcp__guided-review__show_explanation',
    file: 'src/A.java',
    position: '2/44',
    why: 'Pentest **A1**',
    what: 'Adds **isClientType**',
  })
  expect(JSON.stringify(call.result)).toContain('side pane')

  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /A\.java/ }))?.text).toBe('📄 A.java')
  // 60 columns - "2/44" - 2 = 54 cells, 2/44 of them done.
  const bar = await ui.find({ type: 'Text', text: /2\/44/ })
  expect(bar?.text).toBe('██' + '░'.repeat(52) + ' 2/44')
  expect((await ui.find({ type: 'Text', text: /Pourquoi/ }))?.text).toBe('🧭 Pourquoi')
  expect((await ui.find({ type: 'Text', text: /Quoi/ }))?.text).toBe('💡 Quoi')
  await ui.unmount()
})

test('empty pane before any file', async $ => {
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text' }))?.text).toBe('No file under review yet.')
  await ui.unmount()
})

const ROW = {
  plugin: 'guided-review',
  component: 'ToolUse',
  requestId: 't1',
  surface: 'terminal',
  props: {
    tool_use_id: 't1',
    tool: 'mcp__guided-review__show_explanation',
    input: { file: 'src/a/A.java', position: '1/44', why: 'long why', what: 'long what' },
    isRunning: false,
    isErrored: false,
    isInterrupted: false,
    isExpanded: false,
  },
} as const

test('the tool row is one line, the full row once expanded', async ($, on) => {
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)

    return <Text>engine row</Text>
  })

  const compact = await $.ui.mount(ROW)
  expect((await compact.find({ type: 'Text' }))?.text).toBe('📄 1/44 · A.java → pane')
  await compact.unmount()

  const full = await $.ui.mount({ ...ROW, props: { ...ROW.props, isExpanded: true } })
  expect((await full.find({ type: 'Text' }))?.text).toBe('engine row')
  await full.unmount()
})

const BAND = {
  plugin: 'guided-review',
  component: 'AbovePrompt',
  surface: 'terminal',
  props: {
    hasSurvey: false,
    isWorking: false,
    maxRows: 10,
    bodyColumns: 100,
    scroll: { offset: 0, bodyRows: 10 },
    view: {},
  },
} as const

test('the band appears once a file is shown, its buttons send the words', async ($, on) => {
  const sent: string[] = []
  on('prompt.submit', (_, e) => {
    sent.push(e.text)
    return { text: e.text }
  })
  on('tool.register', () => ({ value: { tool: 'mcp__guided-review__show_explanation' } }))
  on('command.register', () => ({ value: { command: 'guided-review' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>engine band</Text>
  })

  const before = await $.ui.mount(BAND)
  expect((await before.find({ type: 'Text' }))?.text).toBe('engine band')
  await before.unmount()

  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.tool.call({ tool: 'mcp__guided-review__show_explanation', file: 'src/A.java', position: '6/44', why: 'w', what: 'w' })

  const band = await $.ui.mount(BAND)
  expect((await band.find({ type: 'Text', text: /6\/44/ }))?.text).toBe('📄 6/44 · A.java')
  for (const key of ['prev', 'next', 'diff']) await band.press({ key })
  expect(sent).toEqual(['précédent', 'suivant', 'réaffiche le diff du fichier courant'])
  await band.unmount()
})
