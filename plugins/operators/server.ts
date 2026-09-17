#!/usr/bin/env bun

import { Server } from '@modelcontextprotocol/sdk/server/index.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js'
import { readFileSync } from 'fs'
import { dirname, join, resolve } from 'path'
import { fileURLToPath } from 'url'
import {
  asObject,
  BunLineStdioTransport,
  clearSessionReservation,
  codexFreshArgv,
  codexResumeArgv,
  content,
  Effort,
  ensureDirs,
  expandHome,
  headFile,
  JsonObject,
  listSessions,
  loadSession,
  loadJson,
  log,
  logPath,
  maybeLoadSession,
  operatorResult,
  optionalBoolean,
  optionalString,
  parseEffort,
  parseBoolean,
  parseSandbox,
  readPromptArg,
  recentLogs,
  requiredString,
  reserveSessionName,
  runForeground,
  runJob,
  Runtime,
  runtimeFromConfig,
  Sandbox,
  startBackground,
  tailFile,
  toolText,
} from './core.ts'

const PLUGIN_DIR = dirname(fileURLToPath(import.meta.url))
const SERVER_PATH = fileURLToPath(import.meta.url)
const CONFIG_PATH = process.env.OPERATORS_CONFIG_PATH ?? join(PLUGIN_DIR, 'config.json')
const CONFIG = loadJson(CONFIG_PATH)
const CODEX_BIN = process.env.OPERATORS_CODEX_BIN ?? 'codex'
const AGY_BIN = process.env.OPERATORS_AGY_BIN ?? 'agy'
const CURSOR_BIN = process.env.OPERATORS_CURSOR_BIN ?? 'cursor-agent'
const RT: Runtime = runtimeFromConfig({
  configPath: CONFIG_PATH,
  stateEnv: 'OPERATORS_STATE_DIR',
  defaultStateDir: '~/.local/state/operators',
})
const AGY_MODELS: Record<string, { model: string; efforts: string[]; defaultEffort: string }> = {
  'gemini-3.1-pro': { model: 'gemini-3.1-pro', efforts: ['low', 'high'], defaultEffort: 'high' },
  'gemini-3.5-flash': { model: 'gemini-3.5-flash', efforts: ['low', 'medium', 'high'], defaultEffort: 'high' },
}
const CURSOR_MODELS = Array.isArray(CONFIG.cursor_models) ? CONFIG.cursor_models.map(String) : []

function stageAfter(record: ReturnType<typeof loadSession> | null, tool: 'implement' | 'critique'): number {
  const current = record?.last_stage ?? (tool === 'implement' ? 1 : 2)
  return current + 1
}

async function codexPlan(args: JsonObject) {
  const session = requiredString(args, 'session')
  const cwd = resolve(expandHome(requiredString(args, 'cwd')))
  const replace = optionalBoolean(args.replace)
  const effort = parseEffort(args.effort, 'xhigh')
  // Preserve implementation sandbox and network defaults:
  // stay sandboxed by default. git commit works fine under workspace-write
  // (plain clone AND worktree, tested) — the actual blocker was outbound
  // network being off by default, which breaks git push/gh/RPC. `network`
  // defaults to true so implementation dispatches keep filesystem sandboxing
  // while getting network back; callers can pass sandbox: 'danger-full-access'
  // for jobs that genuinely need broader access.
  const sandbox = parseSandbox(args.sandbox, 'workspace-write')
  const network = parseBoolean(args.network, true)
  const brief = readFileSync(expandHome(requiredString(args, 'brief_path')), 'utf8')
  const directive =
    `${brief.trim()}\n\n## Stage-1 task: Explain your implementation plan\n\n` +
    'Before writing any code, walk through how you intend to implement this brief. Do NOT start implementing. Output the plan as markdown. Stop after the plan.\n'
  const path = logPath(RT, session, 'codex-plan')
  const intent = {
    kind: 'codex_fresh' as const,
    session,
    role: 'implement' as const,
    cwd,
    effort,
    sandbox,
    network,
    model: null,
    journalPath: null,
    journalMode: null,
    journalMessage: null,
    lastStage: 1,
    register: true,
  }
  const argv = codexFreshArgv(CODEX_BIN, cwd, sandbox, network, effort, null)
  if (optionalBoolean(args.background)) {
    const job = await startBackground(RT, SERVER_PATH, session, argv, cwd, directive, path, intent, replace)
    return content(toolText(`background job started: ${job}`, { job, session, status: 'running', log_path: path }))
  }
  reserveSessionName(RT, session, replace)
  let result: Awaited<ReturnType<typeof runForeground>>
  try {
    result = await runForeground(RT, argv, cwd, directive, path, intent)
    if (!result.final.ok) clearSessionReservation(RT, session)
  } catch (err) {
    clearSessionReservation(RT, session)
    throw err
  }
  const { run, final } = result
  return content(
    toolText(final.ok ? tailFile(RT, path) : `codex_plan failed: ${final.error}\n\n## log head\n${headFile(RT, path)}`, {
      session,
      codex_session_id: final.codexSessionId,
      duration_ms: run.durationMs,
      exit_code: run.exitCode,
      log_path: path,
    }),
    !final.ok,
  )
}

async function codexExec(args: JsonObject) {
  const cwd = resolve(expandHome(requiredString(args, 'cwd')))
  const session = optionalString(args.session) ?? 'codex-exec'
  const effort: Effort = parseEffort(args.effort, 'medium')
  // See codexPlan for sandbox/network defaults.
  const sandbox: Sandbox = parseSandbox(args.sandbox, 'workspace-write')
  const network = parseBoolean(args.network, true)
  const prompt = readPromptArg(args, 'brief', 'brief_path')
  const path = logPath(RT, session, 'codex-exec')
  const intent = {
    kind: 'codex_fresh' as const,
    session,
    role: 'implement' as const,
    cwd,
    effort,
    sandbox,
    network,
    model: null,
    journalPath: null,
    journalMode: null,
    journalMessage: null,
    lastStage: null,
    register: false,
  }
  const argv = codexFreshArgv(CODEX_BIN, cwd, sandbox, network, effort, null)
  if (optionalBoolean(args.background)) {
    const job = await startBackground(RT, SERVER_PATH, session, argv, cwd, prompt, path, intent)
    return content(toolText(`background job started: ${job}`, { job, status: 'running', log_path: path }))
  }
  const { run, final } = await runForeground(RT, argv, cwd, prompt, path, intent)
  return content(
    toolText(final.ok ? tailFile(RT, path) : `codex_exec failed: ${final.error}\n\n## log head\n${headFile(RT, path)}`, {
      codex_session_id: final.codexSessionId,
      duration_ms: run.durationMs,
      exit_code: run.exitCode,
      log_path: path,
    }),
    !final.ok,
  )
}

async function codexImplement(args: JsonObject) {
  const session = requiredString(args, 'session')
  const record = loadSession(RT, session)
  const directive = readPromptArg(args, 'directive', 'directive_path')
  const nextStage = stageAfter(record, 'implement')
  const path = logPath(RT, session, `codex-stage${nextStage}`)
  const intent = { kind: 'codex_resume' as const, session, journalMode: null, journalMessage: null, lastStage: nextStage }
  const argv = codexResumeArgv(CODEX_BIN, record)
  if (optionalBoolean(args.background)) {
    const job = await startBackground(RT, SERVER_PATH, session, argv, record.cwd, directive, path, intent)
    return content(toolText(`background job started: ${job}`, { job, session, status: 'running', log_path: path }))
  }
  const { run, final } = await runForeground(RT, argv, record.cwd, directive, path, intent)
  return content(
    toolText(final.ok ? tailFile(RT, path) : `codex_implement failed: ${final.error}\n\n${tailFile(RT, path)}`, {
      session,
      codex_session_id: final.codexSessionId ?? record.codex_session_id,
      duration_ms: run.durationMs,
      exit_code: run.exitCode,
      log_path: path,
      last_stage: nextStage,
    }),
    !final.ok,
  )
}

async function codexCritique(args: JsonObject) {
  const session = requiredString(args, 'session')
  const record = loadSession(RT, session)
  const question =
    optionalString(args.question) ??
    'Is there any work left to do on this feature? Or anything else you see that should be polished to make the code better? Recommend next steps.'
  const nextStage = stageAfter(record, 'critique')
  const path = logPath(RT, session, `codex-stage${nextStage}`)
  const intent = { kind: 'codex_resume' as const, session, journalMode: null, journalMessage: null, lastStage: nextStage }
  const { run, final } = await runForeground(RT, codexResumeArgv(CODEX_BIN, record), record.cwd, question, path, intent)
  return content(
    toolText(final.ok ? tailFile(RT, path) : `codex_critique failed: ${final.error}\n\n${tailFile(RT, path)}`, {
      session,
      codex_session_id: final.codexSessionId ?? record.codex_session_id,
      duration_ms: run.durationMs,
      exit_code: run.exitCode,
      log_path: path,
      last_stage: nextStage,
    }),
    !final.ok,
  )
}

function codexSessions(args: JsonObject) {
  const name = optionalString(args.name)
  if (name) {
    const record = loadSession(RT, name)
    return content(JSON.stringify({ ...record, recent_logs: recentLogs(RT, record.name) }, null, 2))
  }
  return content(JSON.stringify(listSessions(RT), null, 2))
}

async function agyAsk(args: JsonObject) {
  const model = requiredString(args, 'model')
  const modelConfig = AGY_MODELS[model]
  if (!modelConfig) throw new Error(`agy model not allowed: ${model}`)
  const effort = optionalString(args.effort) ?? modelConfig.defaultEffort
  if (!modelConfig.efforts.includes(effort)) {
    throw new Error(`agy effort not allowed for ${model}: ${effort} (allowed: ${modelConfig.efforts.join(', ')})`)
  }
  const prompt = readPromptArg(args, 'prompt', 'prompt_path')
  const finalPrompt = optionalBoolean(args.raw)
    ? prompt
    : `${prompt.trim()}\n\nDo NOT publish, send messages, or use other side-effect tools. Output only your analysis.`
  const cwd = resolve(expandHome(requiredString(args, 'cwd')))
  const argv = [AGY_BIN, '--model', modelConfig.model]
  const addDirs = Array.isArray(args.add_dirs) ? args.add_dirs.map(String) : []
  for (const dir of addDirs) argv.push('--add-dir', expandHome(dir))
  argv.push('--sandbox', '--dangerously-skip-permissions', '--effort', effort, '-p', finalPrompt)
  const path = logPath(RT, 'agy', 'ask')
  const { run, final } = await runForeground(RT, argv, cwd, '', path, null)
  return content(
    toolText(final.ok ? tailFile(RT, path) : `agy_ask failed: ${final.error}\n\n${tailFile(RT, path)}`, {
      model,
      effort,
      duration_ms: run.durationMs,
      exit_code: run.exitCode,
      log_path: path,
    }),
    !final.ok,
  )
}

async function cursorAsk(args: JsonObject) {
  const model = requiredString(args, 'model')
  if (!CURSOR_MODELS.includes(model)) throw new Error(`cursor model not allowed: ${model}`)
  const prompt = readPromptArg(args, 'prompt', 'prompt_path')
  const cwd = resolve(expandHome(requiredString(args, 'cwd')))
  const argv = [CURSOR_BIN, '-p', '--force', '--model', model, '--output-format', 'text']
  const path = logPath(RT, 'cursor', 'ask')
  const { run, final } = await runForeground(RT, argv, cwd, prompt, path, null)
  return content(
    toolText(final.ok ? tailFile(RT, path) : `cursor_ask failed: ${final.error}\n\n${tailFile(RT, path)}`, {
      model,
      duration_ms: run.durationMs,
      exit_code: run.exitCode,
      log_path: path,
    }),
    !final.ok,
  )
}

const tools = [
  { name: 'codex_plan', description: 'Stage 1 plan-only Codex dispatch.', inputSchema: { type: 'object', properties: { session: { type: 'string' }, brief_path: { type: 'string' }, cwd: { type: 'string' }, effort: { type: 'string', enum: ['low', 'medium', 'high', 'xhigh'] }, sandbox: { type: 'string', enum: ['workspace-write', 'danger-full-access'] }, network: { type: 'boolean', description: 'Under workspace-write, whether outbound network is enabled (default true) via sandbox_workspace_write.network_access. No effect under danger-full-access.' }, background: { type: 'boolean' }, replace: { type: 'boolean' } }, required: ['session', 'brief_path', 'cwd'] } },
  { name: 'codex_exec', description: 'One-shot fresh Codex dispatch with no registry entry.', inputSchema: { type: 'object', properties: { session: { type: 'string' }, brief: { type: 'string' }, brief_path: { type: 'string' }, cwd: { type: 'string' }, effort: { type: 'string', enum: ['low', 'medium', 'high', 'xhigh'] }, sandbox: { type: 'string', enum: ['workspace-write', 'danger-full-access'] }, network: { type: 'boolean', description: 'Under workspace-write, whether outbound network is enabled (default true) via sandbox_workspace_write.network_access. No effect under danger-full-access.' }, background: { type: 'boolean' } }, required: ['cwd'] } },
  { name: 'codex_implement', description: 'Resume a staged Codex implementation session.', inputSchema: { type: 'object', properties: { session: { type: 'string' }, directive: { type: 'string' }, directive_path: { type: 'string' }, background: { type: 'boolean' } }, required: ['session'] } },
  { name: 'codex_critique', description: 'Resume Codex for self-critique.', inputSchema: { type: 'object', properties: { session: { type: 'string' }, question: { type: 'string' } }, required: ['session'] } },
  { name: 'codex_result', description: 'Fetch a background Codex job.', inputSchema: { type: 'object', properties: { job: { type: 'string' }, wait_seconds: { type: 'number' } }, required: ['job'] } },
  { name: 'agy_ask', description: 'One-shot Gemini-only agy dispatch.', inputSchema: { type: 'object', properties: { prompt: { type: 'string' }, prompt_path: { type: 'string' }, model: { type: 'string', enum: Object.keys(AGY_MODELS) }, effort: { type: 'string', enum: ['low', 'high'], description: 'Model-specific effort: gemini-3.1-pro accepts low/high; gemini-3.5-flash accepts low/medium/high. Omitting effort selects the model default.' }, add_dirs: { type: 'array', items: { type: 'string' } }, cwd: { type: 'string' }, raw: { type: 'boolean' } }, required: ['model', 'cwd'] } },
  { name: 'cursor_ask', description: 'One-shot Cursor dispatch for configured GPT/Codex and Opus 4.6 models.', inputSchema: { type: 'object', properties: { prompt: { type: 'string' }, prompt_path: { type: 'string' }, model: { type: 'string', enum: CURSOR_MODELS }, cwd: { type: 'string' } }, required: ['model', 'cwd'] } },
  { name: 'operator_sessions', description: 'List Codex implementation sessions.', inputSchema: { type: 'object', properties: { name: { type: 'string' } } } },
]

// Keep in sync with .claude-plugin/plugin.json — a server advertising a version
// the plugin no longer ships makes deployed behavior impossible to correlate
// with a release.
const mcp = new Server({ name: 'operators', version: '0.2.2' }, { capabilities: { tools: {} } })
mcp.setRequestHandler(ListToolsRequestSchema, async () => ({ tools }))
mcp.setRequestHandler(CallToolRequestSchema, async req => {
  const args = asObject(req.params.arguments)
  try {
    switch (req.params.name) {
      case 'codex_plan':
        return await codexPlan(args)
      case 'codex_exec':
        return await codexExec(args)
      case 'codex_implement':
        return await codexImplement(args)
      case 'codex_critique':
        return await codexCritique(args)
      case 'codex_result':
        return await operatorResult(RT, requiredString(args, 'job'), args.wait_seconds)
      case 'agy_ask':
        return await agyAsk(args)
      case 'cursor_ask':
        return await cursorAsk(args)
      case 'operator_sessions':
        return codexSessions(args)
      default:
        return content(`unknown tool: ${req.params.name}`, true)
    }
  } catch (err) {
    return content(`${req.params.name} failed: ${err instanceof Error ? err.message : String(err)}`, true)
  }
})

ensureDirs(RT)
if (process.argv[2] === '__run_job') {
  try {
    await runJob(RT, requiredString({ spec: process.argv[3] }, 'spec'))
    process.exit(0)
  } catch (err) {
    log('operators', `job runner failed: ${err instanceof Error ? (err.stack ?? err.message) : String(err)}`)
    process.exit(1)
  }
}

await mcp.connect((process.env.OPERATORS_TEST_TRANSPORT === 'bun-line' ? new BunLineStdioTransport() : new StdioServerTransport()) as never)
log('operators', `ready state=${RT.stateDir}`)
