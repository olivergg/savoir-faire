export type Explanation = { file: string; position: string; why: string; what: string }

declare module 'claude-code' {
  interface PluginState {
    'guided-review': { explanation: Shaped<Explanation | null> }
  }
}
