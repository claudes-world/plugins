#!/usr/bin/env bun

import { Server } from '@modelcontextprotocol/sdk/server/index.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js'
import { dirname, join, resolve } from 'path'
import { fileURLToPath } from 'url'
import {
  asObject,
  BunLineStdioTransport,
  clearSessionReservation,
  codexFreshArgv,
  codexResumeArgv,
  content,
  ensureDirs,
  expandHome,
  headFile,
  JsonObject,
  listSessions,
  loadSession,
  log,
  logPath,
  maybeLoadSession,
  optionalBoolean,
  optionalString,
  parseEffort,
  parseBoolean,
  parseSandbox,
  reserveSessionName,
  Runtime,
  runtimeFromConfig,
  requiredString,
  runForeground,
  tailFile,
  toolText,
} from './core.ts'

const PLUGIN_DIR = dirname(fileURLToPath(import.meta.url))
const CODEX_BIN = process.env.WINGMAN_CODEX_BIN ?? process.env.OPERATORS_CODEX_BIN ?? 'codex'
const WINGMAN_MODEL = 'gpt-6-astra'
const RT: Runtime = runtimeFromConfig({
  configPath: process.env.WINGMAN_CONFIG_PATH ?? join(PLUGIN_DIR, 'config.json'),
  stateEnv: 'WINGMAN_STATE_DIR',
  defaultStateDir: '~/.local/state/wingman',
})

const WINGMAN_MODES: Record<string, string> = {
  'open-question': 'Treat this as an open research question. Explore the tradeoffs and answer directly.',
  'plan-first-critique': 'First restate a concise plan, then critique that plan before giving your recommendation.',
  'ask-first': 'Ask clarifying questions first if the request is under-specified. Otherwise answer directly.',
  'stress-test-my-conclusion': 'Stress-test my conclusion. Try to break it, then say what still survives.',
  synthesize: 'Synthesize the relevant evidence into a concise recommendation.',
}

function wingmanPrompt(mode: string, message: string): string {
  return `${WINGMAN_MODES[mode] ?? WINGMAN_MODES['open-question']}\n\nUser message:\n${message}\n`
}

async function wingmanAsk(args: JsonObject) {
  const session = requiredString(args, 'session')
  const message = requiredString(args, 'message')
  const mode = optionalString(args.mode) ?? 'open-question'
  const prompt = wingmanPrompt(mode, message)
  const fresh = asObject(args.new)
  let record = maybeLoadSession(RT, session)

  if (Object.keys(fresh).length > 0) {
    const replace = optionalBoolean(args.replace)
    const cwd = resolve(expandHome(requiredString(fresh, 'cwd')))
    // Fresh co-researcher sessions use the default model.
    // Keep the existing low effort; callers can still override effort.
    const effort = parseEffort(fresh.effort, 'low')
    const sandbox = parseSandbox(fresh.sandbox, 'workspace-write')
    // Wingman is a read/dialog co-researcher role, not implementation —
    // network stays off by default, unlike operators. Callers can
    // still opt in per-session if a research task genuinely needs it.
    const network = parseBoolean(fresh.network, false)
    const journalPath = optionalString(fresh.journal) ?? null
    const path = logPath(RT, session, 'wingman')
    const intent = {
      kind: 'codex_fresh' as const,
      session,
      role: 'wingman' as const,
      cwd,
      effort,
      sandbox,
      network,
      model: WINGMAN_MODEL,
      journalPath,
      journalMode: mode,
      journalMessage: message,
      lastStage: null,
      register: true,
    }
    reserveSessionName(RT, session, replace)
    let result: Awaited<ReturnType<typeof runForeground>>
    try {
      result = await runForeground(RT, codexFreshArgv(CODEX_BIN, cwd, sandbox, network, effort, WINGMAN_MODEL), cwd, prompt, path, intent)
      if (!result.final.ok) clearSessionReservation(RT, session)
    } catch (err) {
      clearSessionReservation(RT, session)
      throw err
    }
    const { run, final } = result
    return content(
      toolText(final.ok ? tailFile(RT, path) : `wingman_ask failed: ${final.error}\n\n## log head\n${headFile(RT, path)}`, {
        session,
        codex_session_id: final.codexSessionId,
        duration_ms: run.durationMs,
        exit_code: run.exitCode,
        log_path: path,
      }),
      !final.ok,
    )
  }

  if (!record) throw new Error(`unknown session ${session}; pass new to create it`)
  const path = logPath(RT, session, 'wingman')
  const intent = { kind: 'codex_resume' as const, session, journalMode: mode, journalMessage: message, lastStage: null }
  const { run, final } = await runForeground(RT, codexResumeArgv(CODEX_BIN, record), record.cwd, prompt, path, intent)
  record = maybeLoadSession(RT, session) ?? record
  return content(
    toolText(final.ok ? tailFile(RT, path) : `wingman_ask failed: ${final.error}\n\n${tailFile(RT, path)}`, {
      session,
      codex_session_id: record.codex_session_id,
      duration_ms: run.durationMs,
      exit_code: run.exitCode,
      log_path: path,
    }),
    !final.ok,
  )
}

function wingmanSessions(args: JsonObject) {
  const name = optionalString(args.name)
  if (name) return content(JSON.stringify(loadSession(RT, name), null, 2))
  return content(JSON.stringify(listSessions(RT), null, 2))
}

const tools = [
  {
    name: 'wingman_ask',
    description: 'Ask or resume a named Codex co-researcher session.',
    inputSchema: {
      type: 'object',
      properties: {
        session: { type: 'string' },
        message: { type: 'string' },
        mode: { type: 'string', enum: ['open-question', 'plan-first-critique', 'ask-first', 'stress-test-my-conclusion', 'synthesize'] },
        new: { type: 'object', properties: { cwd: { type: 'string' }, effort: { type: 'string', enum: ['low', 'medium', 'high', 'xhigh'] }, sandbox: { type: 'string', enum: ['workspace-write', 'danger-full-access'] }, network: { type: 'boolean', description: 'Enable outbound network under workspace-write (default false — wingman is read/dialog by default).' }, journal: { type: 'string' } }, required: ['cwd'] },
        replace: { type: 'boolean' },
      },
      required: ['session', 'message'],
    },
  },
  { name: 'wingman_sessions', description: 'List or inspect wingman sessions.', inputSchema: { type: 'object', properties: { name: { type: 'string' } } } },
]

const mcp = new Server({ name: 'wingman', version: '0.2.3' }, { capabilities: { tools: {} } })
mcp.setRequestHandler(ListToolsRequestSchema, async () => ({ tools }))
mcp.setRequestHandler(CallToolRequestSchema, async req => {
  const args = asObject(req.params.arguments)
  try {
    if (req.params.name === 'wingman_ask') return await wingmanAsk(args)
    if (req.params.name === 'wingman_sessions') return wingmanSessions(args)
    return content(`unknown tool: ${req.params.name}`, true)
  } catch (err) {
    return content(`${req.params.name} failed: ${err instanceof Error ? err.message : String(err)}`, true)
  }
})

ensureDirs(RT)
await mcp.connect((process.env.WINGMAN_TEST_TRANSPORT === 'bun-line' ? new BunLineStdioTransport() : new StdioServerTransport()) as never)
log('wingman', `ready state=${RT.stateDir}`)
