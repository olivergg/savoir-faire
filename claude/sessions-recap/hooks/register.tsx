import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, Timer, UiPressArgument } from 'claude-code'

import type { Project, Recap, Session, View } from '../types'

const PANE = 'sessions-recap'
const TITLE = 'Sessions'
const SCRIPT = '.agents/skills/all-sessions-recap/scripts/session_recap.py'
const DAYS = [1, 7, 14]
const REFRESH_MS = 120_000
// Fetched per project: enough for the flat list's newest FLAT_LIMIT to be exact.
const FETCH_PER_PROJECT = 40
const PER_PROJECT = 10
const FLAT_LIMIT = 40
const STORE_KEY = 'summaries'

const data = atom({ plugin: 'sessions-recap', key: 'data' } as const, null, { shape: 'data-2' })
const view = atom(
  { plugin: 'sessions-recap', key: 'view' } as const,
  { sort: 'recent', group: 'project', days: 7, toggled: [], session: null, pending: [], loading: false, error: null, query: '' },
  { shape: 'view-5' },
)
const results = atom({ plugin: 'sessions-recap', key: 'results' } as const, null, { shape: 'results-1' })
const summaries = atom({ plugin: 'sessions-recap', key: 'summaries' } as const, {}, { shape: 'summaries-1' })

// A summary stays valid until the session moves on.
const summaryKey = (s: Session) => `${s.id}@${s.last_ts}`

const toggle = (list: string[], item: string) =>
  list.includes(item) ? list.filter(one => one !== item) : [...list, item]

const dot = (iso: string, now: number) => {
  const hours = (now - Date.parse(iso)) / 3_600_000
  return hours < 3 ? '🟢' : hours < 24 ? '🟡' : '⚪'
}

const shellQuote = (path: string) => (/^[\w./~-]+$/.test(path) ? path : `'${path.replaceAll("'", `'\\''`)}'`)

const plural = (n: number) => `${n} session${n === 1 ? '' : 's'}`

const sorted = (projects: Project[], sort: View['sort']) =>
  [...projects].sort((a, b) =>
    sort === 'score' ? b.score - a.score : Date.parse(b.last_active) - Date.parse(a.last_active),
  )

// Branches in the order their most recent session appears (sessions come newest first).
const byBranch = (sessions: Session[]) => {
  const groups = new Map<string, Session[]>()
  for (const s of sessions) groups.set(s.branch ?? '', [...(groups.get(s.branch ?? '') ?? []), s])
  return [...groups]
}

const runScript = async ($: EngineInterface, args: string[]) => {
  const home = await $.env.get('HOME')
  const r = await $.process.run(['python3', `${home}/${SCRIPT}`, ...args], { timeoutMs: 60_000 })
  if (r.exitCode !== 0) throw new Error(r.stderr.trim().slice(-300) || `exit ${r.exitCode}`)
  return JSON.parse(r.stdout) as unknown
}

const load = async ($: EngineInterface) => {
  const { days, query } = await read($, view)
  await update($, view, v => ({ ...v, loading: true, error: null }))
  let error: string | null = null
  try {
    if (query) {
      const found = (await runScript($, ['search', query, '--json', '--days', String(days), '--no-git-status'])) as Recap
      await update($, results, () => found)
    } else {
      const recap = (await runScript($, ['recap', '--json', '--days', String(days), '--top-titles', String(FETCH_PER_PROJECT)])) as Recap
      await update($, data, () => recap)
    }
  } catch (err) {
    error = String(err)
  }
  await update($, view, v => ({ ...v, loading: false, error }))
}

const SYSTEM = `You recap one Claude Code session for its author, from their own turns.
Answer with one line of at most 25 words: what was asked and where it landed.
Same language as the turns. No preamble, no quotes.`

type Shown = { turns: [string, string][]; turns_total: number; last_assistant_text: string | null }

const summarize = async ($: EngineInterface, project: Project, s: Session) => {
  await update($, view, v => ({ ...v, pending: [...v.pending, s.id] }))
  try {
    const shown = (await runScript($, ['show', s.id, '--json', '--max-turns', '8'])) as Shown
    const prompt = [
      `Project: ${project.name}`, `Branch: ${s.branch ?? '-'}`, `Auto-title: ${s.title ?? '-'}`,
      `Human turns (${shown.turns_total}, sampled):`,
      ...shown.turns.map(([, t], i) => `${i + 1}. ${t}`),
      `Last assistant note: ${shown.last_assistant_text ?? '-'}`,
    ].join('\n')
    const r = await $.model.complete({ model: 'haiku', system: SYSTEM, prompt, maxTokens: 200, effort: 'low' })
    if (r.isAnswered) {
      const all = await update($, summaries, m => ({ ...m, [summaryKey(s)]: r.text.trim() }))
      await $.store.set(STORE_KEY, all)
    } else $.ui.toast(`No summary: ${r.reason}`)
  } catch (err) {
    $.ui.toast(`Summary failed: ${String(err)}`)
  }
  await update($, view, v => ({ ...v, pending: v.pending.filter(id => id !== s.id) }))
}

const open = async ($: EngineInterface) => {
  await $.ui.open({ id: PANE, title: TITLE })
  if (!(await read($, data))) await load($)
}

export const register: Register = on => {
  let timer: Timer | undefined

  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'sessions-recap',
      description: 'Open a pane ranking your Claude Code sessions across projects',
    })
    const stored = await $.store.get(STORE_KEY)
    if (stored && typeof stored === 'object') {
      await update($, summaries, m => ({ ...(stored as Record<string, string>), ...m }))
    }
    timer?.cancel()
    timer = $.clock.every(REFRESH_MS, () => {
      void (async () => {
        try {
          if (!(await read($, view)).loading && (await read($, data))) await load($)
        } catch {
          // A failed refresh shows on the next manual one.
        }
      })()
    })

    return next(e)
  })

  on('command.run', { command: 'sessions-recap' }, async $ => {
    await open($)

    return { text: 'Sessions pane opened.' }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const elements = $.ui.resolve(e)
    const { Box, Text, Button } = elements
    // Mobile has no Input: no search there.
    const Input = 'Input' in elements ? elements.Input : undefined
    const recap = await read($, data)
    const found = await read($, results)
    const v = await read($, view)
    const sums = await read($, summaries)
    const now = Date.now()
    const set = (fn: (v: View) => View) => void update($, view, fn)

    const sessionRow = (p: Project, s: Session, withContext = false) => {
      const summary = s.recap ?? sums[summaryKey(s)]
      const isOpen = v.session === s.id
      const isPending = v.pending.includes(s.id)
      // `--resume <id>` only finds sessions of the current directory's project.
      const resume = `cd ${shellQuote(p.cwd)} && claude --resume ${s.id}`
      const press = (e: UiPressArgument) => {
        void $.ui.copy({ text: resume, surface: e.surface })
        $.ui.toast(`Copied: ${resume}`)
        if (!s.recap) set(x => ({ ...x, session: isOpen ? null : s.id }))
      }

      return (
        <Box key={`s:${s.id}`} flexDirection="column" paddingLeft={withContext ? 0 : 4}>
          {withContext && (
            <Text dimColor wrap="truncate-end">
              {p.emoji} {p.name} <Text color="magenta">⎇ {s.branch || '(no branch)'}</Text>
              {s.ahead_behind ? ` ${s.ahead_behind}` : ''}
            </Text>
          )}
          <Box flexDirection="row">
            <Button key={`s:${s.id}`} plain onPress={press}>
              {dot(s.last_ts, now)} <Text dimColor>{s.age.replace(' ago', '').padEnd(5)}</Text>
            </Button>
            {summary ? <Text wrap="wrap">{summary}</Text> : <Text dimColor wrap="wrap">{s.title ?? '(untitled)'}</Text>}
          </Box>
          {s.snippet && (
            <Box paddingLeft={9}>
              <Text dimColor wrap="wrap">{s.hits}× {s.snippet}</Text>
            </Box>
          )}
          {isOpen && !s.recap && (
            <Box paddingLeft={9}>
              <Button key={`sum:${s.id}`} onPress={() => void summarize($, p, s)}>
                {isPending ? 'summarizing…' : summary ? 'resummarize' : 'summarize'}
              </Button>
            </Box>
          )}
        </Box>
      )
    }

    const projectRow = (p: Project) => {
      // Projects start closed; `toggled` holds the ones opened.
      const isOpen = v.toggled.includes(p.cwd)

      return (
        <Box key={`p:${p.cwd}`} flexDirection="column">
          <Button key={`p:${p.cwd}`} plain onPress={() => set(x => ({ ...x, toggled: toggle(x.toggled, p.cwd) }))}>
            {isOpen ? '▾' : '▸'} {dot(p.last_active, now)} {p.emoji} <Text bold>{p.name}</Text>{' '}
            <Text dimColor>{plural(p.session_count)}</Text>
          </Button>
          {isOpen &&
            byBranch(p.sessions.slice(0, PER_PROJECT)).map(([branch, sessions]) => (
              <Box key={`b:${p.cwd}:${branch}`} flexDirection="column">
                <Text color="magenta">
                  {'  '}⎇ {branch || '(no branch)'}
                  {sessions[0]?.ahead_behind ? <Text dimColor> {sessions[0].ahead_behind}</Text> : ''}
                </Text>
                {sessions.map(s => sessionRow(p, s))}
              </Box>
            ))}
        </Box>
      )
    }

    const flat = (projects: Project[]) =>
      projects
        .flatMap(p => p.sessions.map(s => [p, s] as const))
        .sort(([, a], [, b]) => Date.parse(b.last_ts) - Date.parse(a.last_ts))
        .slice(0, FLAT_LIMIT)
        .map(([p, s]) => sessionRow(p, s, true))

    // An empty submit goes back to the recap, reloaded as `days` may have changed meanwhile.
    const search = (text: string) => void update($, view, x => ({ ...x, query: text.trim() })).then(() => load($))

    const body = () => {
      if (v.query) {
        if (!found) return <Text dimColor>Searching…</Text>
        if (found.projects.length === 0) return <Text dimColor>No match for “{v.query}” in the last {v.days} day(s).</Text>
        return flat(found.projects)
      }
      if (!recap) return v.error ? null : <Text dimColor>Loading sessions…</Text>
      if (recap.projects.length === 0) return <Text dimColor>No sessions in the last {v.days} day(s).</Text>
      return v.group === 'flat' ? flat(recap.projects) : sorted(recap.projects, v.sort).map(projectRow)
    }

    return (
      <Box flexDirection="column">
        <Box flexDirection="row" gap={1}>
          {Input && <Input key="q" placeholder="search all turns…" submitLabel="search" value={v.query} onSubmit={search} />}
          {v.query && (
            <Button key="clear" onPress={() => search('')}>
              clear
            </Button>
          )}
        </Box>
        <Box flexDirection="row" gap={1}>
          {!v.query && (
            <Button key="group" hotkey="g" onPress={() => set(x => ({ ...x, group: x.group === 'flat' ? 'project' : 'flat' }))}>
              {v.group === 'flat' ? 'by session' : 'by project'}
            </Button>
          )}
          {!v.query && v.group === 'project' && (
            <Button key="sort" hotkey="s" onPress={() => set(x => ({ ...x, sort: x.sort === 'score' ? 'recent' : 'score' }))}>
              sort: {v.sort}
            </Button>
          )}
          {DAYS.map(d => (
            <Button
              key={`days:${d}`}
              {...(d === v.days ? { variant: 'primary' as const } : {})}
              onPress={() => void update($, view, x => ({ ...x, days: d })).then(() => load($))}
            >
              {d}d
            </Button>
          ))}
          <Button key="refresh" hotkey="r" onPress={() => void load($)}>
            {v.loading ? 'loading…' : 'refresh'}
          </Button>
        </Box>
        {v.error && <Text color="error">{v.error}</Text>}
        {body()}
      </Box>
    )
  })
}
