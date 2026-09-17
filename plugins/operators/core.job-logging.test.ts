import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { existsSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import {
  ensureDirs,
  loadJob,
  operatorResult,
  runCli,
  runForeground,
  Runtime,
  startBackground,
  writeJob,
} from './core.ts'

let root = ''
const childPids = new Set<number>()

function runtime(path: string): Runtime {
  return {
    stateDir: path,
    sessionDir: join(path, 'sessions'),
    logDir: join(path, 'logs'),
    jobDir: join(path, 'jobs'),
    stdinDir: join(path, 'stdin'),
    logTailBytes: 20_000,
    logHeadBytes: 4_000,
    maxWaitSeconds: 2,
  }
}

async function waitFor(check: () => boolean, message: string, timeoutMs = 2_000): Promise<void> {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (check()) return
    await Bun.sleep(20)
  }
  throw new Error(`timed out waiting for ${message}`)
}

function text(result: Awaited<ReturnType<typeof operatorResult>>): string {
  return result.content[0]?.text ?? ''
}

beforeEach(() => {
  root = mkdtempSync(join(tmpdir(), 'operators-job-logging.'))
})

afterEach(() => {
  for (const pid of childPids) {
    try {
      process.kill(pid, 'SIGKILL')
    } catch {}
  }
  childPids.clear()
  rmSync(root, { recursive: true, force: true })
})

describe('runCli streaming logs', () => {
  test('creates a private log containing output while the child is still running', async () => {
    const path = join(root, 'live.log')
    let finished = false
    const running = runCli(
      [
        process.execPath,
        '-e',
        "process.stdout.write('first byte\\n'); process.stderr.write('stderr byte\\n'); await Bun.sleep(800); process.stdout.write('finished\\n')",
      ],
      root,
      '',
      path,
    ).finally(() => {
      finished = true
    })

    await waitFor(() => existsSync(path) && readFileSync(path, 'utf8').includes('first byte'), 'live output')
    expect(finished).toBe(false)
    expect(statSync(path).mode & 0o777).toBe(0o600)

    const result = await running
    expect(result.combinedText).toContain('first byte')
    expect(result.combinedText).toContain('stderr byte')
    expect(result.combinedText).toContain('finished')
    expect(result.stdoutText).toBe(result.combinedText)
  })

  test('keeps partial output when the child is killed mid-run', async () => {
    const path = join(root, 'killed.log')
    const pidPath = join(root, 'child.pid')
    const running = runCli(
      [
        process.execPath,
        '-e',
        `process.stdout.write('partial before kill\\n'); await Bun.write(${JSON.stringify(pidPath)}, String(process.pid)); await Bun.sleep(30_000)`,
      ],
      root,
      '',
      path,
    )

    await waitFor(() => existsSync(pidPath) && readFileSync(path, 'utf8').includes('partial before kill'), 'child pid and partial output')
    const pid = Number(readFileSync(pidPath, 'utf8'))
    childPids.add(pid)
    process.kill(pid, 'SIGKILL')
    const result = await running
    childPids.delete(pid)

    expect(result.exitCode).not.toBe(0)
    expect(readFileSync(path, 'utf8')).toContain('partial before kill')
    expect(result.combinedText).toContain('partial before kill')
  })

  test('keeps stderr in the log but excludes it from a completed codex journal entry', async () => {
    const rt = runtime(join(root, 'state'))
    ensureDirs(rt)
    const log = join(rt.logDir, 'journal.log')
    const journal = join(root, 'journal.md')
    const fakeCodex = join(root, 'fake-codex.ts')
    const sessionId = '12345678-1234-1234-1234-123456789abc'
    writeFileSync(
      fakeCodex,
      `const outputIndex = process.argv.indexOf('--output-last-message')
if (outputIndex === -1) throw new Error('missing output capture argument')
await Bun.write(process.argv[outputIndex + 1]!, 'clean reply\\n')
process.stderr.write('session id: ${sessionId}\\nstderr warning\\n')
`,
    )
    const { run, final } = await runForeground(
      rt,
      [process.execPath, fakeCodex],
      root,
      '',
      log,
      {
        kind: 'codex_fresh',
        session: 'journal-test',
        role: 'wingman',
        cwd: root,
        effort: 'medium',
        sandbox: 'workspace-write',
        network: false,
        model: null,
        journalPath: journal,
        journalMode: 'test',
        journalMessage: 'say hello',
        lastStage: null,
        register: false,
      },
    )

    expect(final.ok).toBe(true)
    expect(run.combinedText).toContain('stderr warning')
    expect(readFileSync(log, 'utf8')).toContain('stderr warning')
    expect(readFileSync(journal, 'utf8')).toContain('**codex:** clean reply')
    expect(readFileSync(journal, 'utf8')).not.toContain('stderr warning')
  })
})

describe('background runner diagnostics', () => {
  test('captures a runner module-resolution crash and records its path', async () => {
    const rt = runtime(join(root, 'state'))
    ensureDirs(rt)
    const serverPath = join(root, 'broken-runner.ts')
    const path = join(rt.logDir, 'job.log')
    writeFileSync(serverPath, "import '@operators-test/missing-runner-module'\n")

    const job = await startBackground(rt, serverPath, 'startup', [process.execPath, '-e', ''], root, '', path, null)
    const record = loadJob(rt, job)
    childPids.add(record.pid)
    expect(record.runner_log_path).toBe(join(rt.logDir, `${job}.runner.log`))

    const spec = JSON.parse(readFileSync(join(rt.jobDir, `${job}.spec.json`), 'utf8'))
    expect(spec.runnerLogPath).toBe(record.runner_log_path)
    await waitFor(
      () => !!record.runner_log_path && existsSync(record.runner_log_path) && readFileSync(record.runner_log_path, 'utf8').length > 0,
      'runner startup error',
    )
    childPids.delete(record.pid)

    expect(statSync(record.runner_log_path!).mode & 0o777).toBe(0o600)
    expect(readFileSync(record.runner_log_path!, 'utf8')).toMatch(/missing-runner-module|Cannot find/)
  })
})

describe('operatorResult abnormal logs', () => {
  test('includes both partial job and runner log tails for an orphaned job', async () => {
    const rt = runtime(join(root, 'state'))
    ensureDirs(rt)
    const jobPath = join(rt.logDir, 'partial.log')
    const runnerPath = join(rt.logDir, 'partial.runner.log')
    writeFileSync(jobPath, 'job partial marker\n')
    writeFileSync(runnerPath, 'runner partial marker\n')
    writeJob(rt, {
      job: 'orphan-with-logs',
      status: 'running',
      pid: 99_999_999,
      started_ts: new Date().toISOString(),
      log_path: jobPath,
      runner_log_path: runnerPath,
    })

    const result = await operatorResult(rt, 'orphan-with-logs', 0)
    expect(result.isError).toBe(true)
    expect(text(result)).toContain('job orphaned: job pid is no longer alive')
    expect(text(result)).toContain('## job log tail\njob partial marker')
    expect(text(result)).toContain('## runner log tail\nrunner partial marker')
    expect(loadJob(rt, 'orphan-with-logs').status).toBe('orphaned')
  })

  test('says plainly when an orphaned job produced no log', async () => {
    const rt = runtime(join(root, 'state'))
    ensureDirs(rt)
    writeJob(rt, {
      job: 'orphan-without-logs',
      status: 'running',
      pid: 99_999_999,
      started_ts: new Date().toISOString(),
      log_path: join(rt.logDir, 'missing.log'),
      runner_log_path: join(rt.logDir, 'missing.runner.log'),
    })

    const result = await operatorResult(rt, 'orphan-without-logs', 0)
    expect(result.isError).toBe(true)
    expect(text(result)).toContain('no log was produced')
  })

  test('includes available log tails for a failed job', async () => {
    const rt = runtime(join(root, 'state'))
    ensureDirs(rt)
    const jobPath = join(rt.logDir, 'failed.log')
    const runnerPath = join(rt.logDir, 'failed.runner.log')
    writeFileSync(jobPath, 'failed job marker\n')
    writeFileSync(runnerPath, 'failed runner marker\n')
    writeJob(rt, {
      job: 'failed-with-logs',
      status: 'failed',
      pid: 99_999_999,
      started_ts: new Date().toISOString(),
      ended_ts: new Date().toISOString(),
      exit_code: 1,
      error: 'exit code 1',
      log_path: jobPath,
      runner_log_path: runnerPath,
    })

    const result = await operatorResult(rt, 'failed-with-logs', 0)
    expect(result.isError).toBe(true)
    expect(text(result)).toContain('## job log tail\nfailed job marker')
    expect(text(result)).toContain('## runner log tail\nfailed runner marker')
  })

  test('includes the job log head when session capture fails beyond the tail window', async () => {
    const rt = runtime(join(root, 'state'))
    ensureDirs(rt)
    const jobPath = join(rt.logDir, 'failed-capture.log')
    writeFileSync(jobPath, `session header marker\n${'x'.repeat(rt.logTailBytes + 1)}\ntail marker\n`)
    writeJob(rt, {
      job: 'failed-capture',
      status: 'failed_capture',
      pid: 99_999_999,
      started_ts: new Date().toISOString(),
      ended_ts: new Date().toISOString(),
      exit_code: 0,
      error: 'could not capture codex session id',
      log_path: jobPath,
    })

    const result = await operatorResult(rt, 'failed-capture', 0)
    expect(result.isError).toBe(true)
    expect(text(result)).toContain('## job log head\nsession header marker')
    expect(text(result)).toContain('## job log tail')
    expect(text(result)).toContain('tail marker')
  })
})
