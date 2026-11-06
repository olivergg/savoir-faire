import { expect, test } from 'claude-code/testing'

const PANE = {
  plugin: 'sessions-recap',
  component: 'Pane',
  requestId: 'sessions-recap',
  props: {
    title: 'Sessions',
    isFocused: false,
    bodyColumns: 80,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 40 },
    view: {},
  },
} as const

const session = (id: string, branch: string, title: string, recap: string | null) => ({
  id, title, recap, branch, ahead_behind: branch === 'main' ? null : '2↑',
  last_ts: new Date().toISOString(), age: 'just now', messages: 10,
})

const RECAP = {
  now: new Date().toISOString(),
  projects: [
    { cwd: '/w/old', name: '~/w/old', emoji: '📁', score: 9, last_active: '2026-01-01T00:00:00+00:00',
      session_count: 1,
      sessions: [{ ...session('a1aaaaaaaa', 'main', 'Old work', null), last_ts: '2026-01-01T00:00:00+00:00' }] },
    { cwd: '/w/new', name: '~/w/new', emoji: '🗄️', score: 1, last_active: new Date().toISOString(),
      session_count: 1, sessions: [session('b1bbbbbbbb', 'feature/x', 'New work', 'Fixed the sink, next: review')] },
  ],
}

test('the pane sorts and opens projects, with each session recap', async ($, on) => {
  on('command.register', () => ({ value: { command: 'sessions-recap' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('env.get', () => ({ value: '/home' }))
  on('store.get', () => ({ value: undefined }))
  on('clock.every', () => ({ value: undefined }))
  on('process.run', () => ({
    value: { exitCode: 0, stdout: JSON.stringify(RECAP), stderr: '', isStdoutTruncated: false, isStderrTruncated: false },
  }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  const copied: string[] = []
  on('ui.copy', (_, e) => (copied.push(e.text), { value: { isCopied: true } }))
  on('ui.toast', () => ({ value: undefined }))

  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({
    command: 'sessions-recap', args: '', origin: { kind: 'composer' },
    presentation: { isFullscreen: true, columns: 200 },
  })

  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  const projects = async () =>
    (await ui.findAll({ type: 'Button' })).map(b => b.key).filter(key => key?.startsWith('p:'))

  expect(await projects()).toEqual(['p:/w/new', 'p:/w/old'])
  expect(await ui.find({ type: 'Text', text: /Fixed the sink/ })).toBeUndefined()
  await ui.press({ key: 'sort' })
  expect(await projects()).toEqual(['p:/w/old', 'p:/w/new'])
  await ui.press({ key: 'sort' })

  await ui.press({ key: 'p:/w/new' })
  expect(await ui.find({ type: 'Text', text: /Fixed the sink/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /feature\/x.*2↑/ })).toBeDefined()

  // A press copies the resume one-liner; a session with Claude Code's own recap offers no summarize.
  await ui.press({ key: 's:b1bbbbbbbb' })
  expect(copied).toEqual(['cd /w/new && claude --resume b1bbbbbbbb'])
  expect(await ui.find({ type: 'Button', key: 'sum:b1bbbbbbbb' })).toBeUndefined()

  await ui.press({ key: 'p:/w/old' })
  expect(await ui.find({ type: 'Text', text: /Old work/ })).toBeDefined()
  await ui.press({ key: 's:a1aaaaaaaa' })
  expect(await ui.find({ type: 'Button', key: 'sum:a1aaaaaaaa' })).toBeDefined()

  // Flat: sessions newest first across projects, each with its folder and branch.
  await ui.press({ key: 'group' })
  expect(await projects()).toEqual([])
  const sessions = (await ui.findAll({ type: 'Button' })).map(b => b.key).filter(key => key?.startsWith('s:'))
  expect(sessions).toEqual(['s:b1bbbbbbbb', 's:a1aaaaaaaa'])
  expect(await ui.find({ type: 'Text', text: /~\/w\/new ⎇ feature\/x 2↑/ })).toBeDefined()
  await ui.unmount()
})

test('a search lists the matching sessions with their excerpt, clear goes back', async ($, on) => {
  const FOUND = {
    now: RECAP.now,
    projects: [{ ...RECAP.projects[0]!, sessions: [{ ...RECAP.projects[0]!.sessions[0]!, hits: 3, snippet: '…the sink leaks…' }] }],
  }
  const runs: string[][] = []
  on('command.register', () => ({ value: { command: 'sessions-recap' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('env.get', () => ({ value: '/home' }))
  on('store.get', () => ({ value: undefined }))
  on('clock.every', () => ({ value: undefined }))
  on('process.run', (_, e) => {
    runs.push([...e.argv])
    const out = e.argv[2] === 'search' ? (e.argv[3] === 'nothing' ? { ...FOUND, projects: [] } : FOUND) : RECAP
    return { value: { exitCode: 0, stdout: JSON.stringify(out), stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  on('session.start', (_, e) => ({ cwd: e.cwd }))

  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({
    command: 'sessions-recap', args: '', origin: { kind: 'composer' },
    presentation: { isFullscreen: true, columns: 200 },
  })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  const sessions = async () =>
    (await ui.findAll({ type: 'Button' })).map(b => b.key).filter(key => key?.startsWith('s:'))

  await ui.input({ key: 'q', text: '  sink ' })
  expect(runs.at(-1)).toEqual(['python3', expect.stringMatching(/session_recap\.py$/), 'search', 'sink', '--json', '--days', '7', '--no-git-status'])
  expect(await sessions()).toEqual(['s:a1aaaaaaaa'])
  expect(await ui.find({ type: 'Text', text: /3× …the sink leaks…/ })).toBeDefined()
  expect(await ui.find({ type: 'Button', key: 'group' })).toBeUndefined()

  await ui.input({ key: 'q', text: 'nothing' })
  expect(await ui.find({ type: 'Text', text: /No match for “nothing”/ })).toBeDefined()

  await ui.press({ key: 'clear' })
  expect(runs.at(-1)?.[2]).toBe('recap')
  expect(await ui.find({ type: 'Button', key: 'group' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /the sink leaks/ })).toBeUndefined()
  await ui.unmount()
})
