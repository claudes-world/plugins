#!/usr/bin/env bash
set -euo pipefail

# Standalone stdio smoke. This may not run in this sandbox because Bun can
# limit subprocess stdin behavior here. It is intentionally not wired into the
# main harness.

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="${WINGMAN_SMOKE_STATE:-$(mktemp -d "${TMPDIR:-/tmp}/wingman-smoke.XXXXXX")}"
DRIVER="$STATE/smoke-stdio.mjs"

mkdir -p "$STATE"

cat > "$DRIVER" <<'JS'
import { spawn } from 'node:child_process'

const pluginDir = process.env.PLUGIN_DIR
const state = process.env.WINGMAN_STATE_DIR
const proc = spawn('bun', ['server.bundle.js'], {
  cwd: pluginDir,
  env: { ...process.env, WINGMAN_STATE_DIR: state },
  stdio: ['pipe', 'pipe', 'pipe'],
})

let stdout = ''
let stderr = ''
proc.stdout.on('data', chunk => {
  stdout += chunk.toString('utf8')
})
proc.stderr.on('data', chunk => {
  stderr += chunk.toString('utf8')
})

function send(message) {
  proc.stdin.write(`${JSON.stringify(message)}\n`)
}

send({ jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'wingman-stdio-smoke', version: '0.0.1' } } })
send({ jsonrpc: '2.0', method: 'notifications/initialized', params: {} })
send({ jsonrpc: '2.0', id: 2, method: 'tools/list', params: {} })
send({ jsonrpc: '2.0', id: 3, method: 'tools/call', params: { name: 'wingman_sessions', arguments: {} } })

const deadline = Date.now() + 5000
while (Date.now() < deadline) {
  const responses = stdout.trim().split('\n').filter(Boolean).map(line => JSON.parse(line))
  if (responses.some(r => r.id === 1) && responses.some(r => r.id === 2) && responses.some(r => r.id === 3)) {
    proc.kill()
    console.log('wingman stdio smoke: ok')
    process.exit(0)
  }
  await new Promise(resolve => setTimeout(resolve, 50))
}

proc.kill()
throw new Error(`missing stdio responses\nstdout:\n${stdout}\nstderr:\n${stderr}`)
JS

PLUGIN_DIR="$PLUGIN_DIR" WINGMAN_STATE_DIR="$STATE/state" bun "$DRIVER"
