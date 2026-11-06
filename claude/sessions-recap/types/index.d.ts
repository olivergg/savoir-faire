// What `session_recap.py recap --json` prints.
export type Session = {
  id: string
  title: string | null
  recap: string | null
  branch: string | null
  ahead_behind: string | null
  last_ts: string
  age: string
  messages: number
  // `search --json` only.
  hits?: number
  snippet?: string
}

export type Project = {
  cwd: string
  name: string
  emoji: string
  score: number
  last_active: string
  session_count: number
  sessions: Session[]
}

export type Recap = { now: string; projects: Project[] }

export type View = {
  sort: 'score' | 'recent'
  // `flat`: every session in one list, newest first, each with its folder and branch.
  group: 'project' | 'flat'
  days: number
  // Projects opened, by cwd.
  toggled: string[]
  session: string | null
  pending: string[]
  loading: boolean
  error: string | null
  // Last submitted search; empty shows the recap.
  query: string
}

declare module 'claude-code' {
  interface PluginState {
    'sessions-recap': {
      data: Shaped<Recap | null>
      view: Shaped<View>
      results: Shaped<Recap | null>
      summaries: Shaped<Record<string, string>>
    }
  }
}
