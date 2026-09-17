import { expect, test } from 'bun:test'
import { mkdtempSync, mkdirSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const root = import.meta.dir
const name = JSON.parse(readFileSync(join(root, '.claude-plugin/plugin.json'), 'utf8')).name
const prefix = name.toUpperCase()

test('installed MCP reports absent optional CLIs and still lists sessions', async () => {
  const scratch = mkdtempSync(join(tmpdir(), `${name}-missing-`))
  const config = JSON.parse(readFileSync(join(root, '.mcp.json'), 'utf8'))
  const entry: any = Object.values(config.mcpServers)[0]
  const command = [entry.command, ...entry.args.map((s: string) => s.replaceAll('${CLAUDE_PLUGIN_ROOT}', root))]
  const absent = join(scratch, 'absent-cli')
  const env = { ...process.env, [`${prefix}_STATE_DIR`]: join(scratch, 'state'),
    [`${prefix}_TEST_TRANSPORT`]: 'bun-line', [`${prefix}_CODEX_BIN`]: absent,
    OPERATORS_AGY_BIN: absent, OPERATORS_CURSOR_BIN: absent }
  const calls = name === 'wingman'
    ? [['wingman_ask', { session: 'missing', message: 'fixture', new: { cwd: scratch } }]]
    : [['codex_exec', { brief: 'fixture', cwd: scratch }],
       ['cursor_ask', { prompt: 'fixture', model: 'gpt-5.3-codex', cwd: scratch }],
       ['agy_ask', { prompt: 'fixture', model: 'gemini-3.5-flash', cwd: scratch }]]
  try {
    const messages: any[] = [
      { jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'fixture', version: '1' } } },
      { jsonrpc: '2.0', method: 'notifications/initialized', params: {} },
      ...calls.map(([tool, args], i) => ({ jsonrpc: '2.0', id: i + 2, method: 'tools/call', params: { name: tool, arguments: args } })),
      { jsonrpc: '2.0', id: 99, method: 'tools/call', params: { name: name === 'wingman' ? 'wingman_sessions' : 'operator_sessions', arguments: {} } },
    ]
    const child = Bun.spawn(command, { cwd: scratch, env, stdin: new Blob([messages.map(m => JSON.stringify(m)).join('\n') + '\n']), stdout: 'pipe', stderr: 'pipe' })
    const output = await new Response(child.stdout).text()
    const error = await new Response(child.stderr).text()
    expect(await child.exited, error).toBe(0)
    const replies = output.trim().split('\n').map(s => JSON.parse(s))
    for (let i = 0; i < calls.length; i++) {
      const result = replies.find(r => r.id === i + 2).result
      expect(result.isError).toBe(true)
      expect(result.content[0].text).toContain('spawn failed')
      expect(result.content[0].text).toContain('absent-cli')
    }
    expect(replies.find(r => r.id === 99).result.isError).not.toBe(true)
    expect(JSON.parse(replies.find(r => r.id === 99).result.content[0].text)).toEqual([])
  } finally { rmSync(scratch, { recursive: true, force: true }) }
}, 15000)
