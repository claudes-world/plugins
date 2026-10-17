import { describe, expect, test } from 'bun:test'
import { existsSync, readFileSync, statSync } from 'fs'
import { join } from 'path'

const root = import.meta.dir
const read = (path: string) => readFileSync(join(root, path), 'utf8')

describe('vnc-computer marketplace layout', () => {
  test('manifest and MCP server declaration', () => {
    const plugin = JSON.parse(read('.claude-plugin/plugin.json'))
    expect(plugin.name).toBe('vnc-computer')
    expect(plugin.version).toMatch(/^\d+\.\d+\.\d+$/)
    for (const keyword of ['vnc', 'remote-desktop', 'computer-use', 'screen-control']) {
      expect(plugin.keywords).toContain(keyword)
    }
    const mcp = JSON.parse(read('.mcp.json'))
    expect(mcp.mcpServers['vnc-computer']).toEqual({
      command: 'python3',
      args: ['${CLAUDE_PLUGIN_ROOT}/server.py'],
    })
  })

  test('scripts are executable and host-portable', () => {
    for (const path of ['server.py', 'bin/setup', 'bin/test-rig', 'bin/frames-concat', 'test/smoke.py']) {
      expect(statSync(join(root, path)).mode & 0o111).not.toBe(0)
      expect(read(path)).not.toMatch(/\/home\/[^/]+\//)
    }
    for (const path of ['vnclib/rfb.py', 'vnclib/crypto.py', 'vnclib/keys.py', 'vnclib/imaging.py', 'vnclib/recorder.py']) {
      expect(existsSync(join(root, path))).toBe(true)
      expect(read(path)).not.toMatch(/\/home\/[^/]+\//)
    }
  })

  test('never encodes video and never takes the password from env', () => {
    for (const path of ['server.py', 'vnclib/recorder.py', 'bin/frames-concat']) {
      expect(read(path)).not.toMatch(/subprocess|os\.system|popen/i)
    }
    expect(read('server.py')).not.toContain("'VNC_PASSWORD'")
  })

  test('refuses to connect without VNC_HOST', () => {
    const request = JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'tools/call', params: { name: 'screenshot', arguments: {} } })
    const result = Bun.spawnSync(['python3', join(root, 'server.py')], {
      stdin: Buffer.from(request + '\n'),
      env: { PATH: process.env.PATH ?? '/usr/bin:/bin', VNC_COMPUTER_NO_VENV: '1' },
    })
    expect(result.exitCode).toBe(0)
    const reply = JSON.parse(result.stdout.toString().trim())
    expect(reply.result.isError).toBe(true)
    expect(reply.result.content[0].text).toContain('VNC_HOST is not set')
  })

  test('rig-free Python unit suite passes', () => {
    const result = Bun.spawnSync(['python3', join(root, 'test/test_unit.py')], {
      env: { PATH: process.env.PATH ?? '/usr/bin:/bin', VNC_COMPUTER_NO_VENV: '1' },
    })
    expect(result.exitCode, result.stderr.toString()).toBe(0)
  }, 60_000)
})
