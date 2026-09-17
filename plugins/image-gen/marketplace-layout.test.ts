import { describe, expect, test } from 'bun:test'
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from 'fs'
import { join } from 'path'
import { tmpdir } from 'os'

describe('image-gen marketplace layout', () => {


  test('vendored CLI exists, is executable, and is host-portable', () => {
    const cli = join(import.meta.dir, 'bin/gen-image')
    expect(existsSync(cli)).toBe(true)
    expect(statSync(cli).mode & 0o111).not.toBe(0)

    const source = readFileSync(cli, 'utf8')
    expect(source.split('\n', 1)[0]).toBe('#!/usr/bin/env python3')
    expect(source).not.toMatch(/\/home\/[^/]+\//)
    // The original bug was two-part: a host venv shebang AND a sys.path escape
    // into the toolbox repo's sibling lib/. A relative escape would carry no
    // literal host path, so guard the mechanism rather than only the string.
    expect(source).not.toContain('sys.path.insert')
  })

  test('CLI rejects provider model flags without enabling another provider', () => {
    const cli = join(import.meta.dir, 'bin/gen-image')
    for (const args of [
      ['--model', 'paid-provider', 'draw a cat'],
      ['--model=paid-provider', 'draw a cat'],
      ['-mpaid-provider', 'draw a cat'],
    ]) {
      const result = Bun.spawnSync([cli, ...args])

      expect(result.exitCode).toBe(2)
      expect(result.stderr.toString().trim()).toBe(
        'Provider model flags are unsupported; use codex image_gen',
      )
    }
  })

  test('missing optional Codex fails explicitly without provider fallback', () => {
    const scratch = mkdtempSync(join(tmpdir(), 'image-gen-missing-'))
    try {
      const python = Bun.which('python3')!
      const result = Bun.spawnSync([python, join(import.meta.dir, 'bin/gen-image'), 'fixture', '-o', join(scratch, 'out.png')], {
        env: { PATH: scratch },
      })
      expect(result.exitCode).toBe(127)
      expect(result.stderr.toString()).toContain('codex CLI not found')
      expect(existsSync(join(scratch, 'out.png'))).toBe(false)
    } finally { rmSync(scratch, { recursive: true, force: true }) }
  })

  test('CLI enables workspace-write network access for Codex image_gen', () => {
    const cli = join(import.meta.dir, 'bin/gen-image')
    const fixture = mkdtempSync(join(tmpdir(), 'gen-image-argv-'))
    const fakeBin = join(fixture, 'bin')
    const fakeCodex = join(fakeBin, 'codex')
    const argvLog = join(fixture, 'argv.log')
    const output = join(fixture, 'output.png')

    try {
      mkdirSync(fakeBin)
      writeFileSync(fakeCodex, '#!/bin/sh\nprintf \'%s\\n\' "$@" > "$GEN_IMAGE_ARGV"\nprintf x > "$GEN_IMAGE_OUTPUT"\n')
      chmodSync(fakeCodex, 0o755)

      const result = Bun.spawnSync([cli, 'draw a cat', '--out', output], {
        env: {
          ...process.env,
          PATH: `${fakeBin}:${process.env.PATH ?? ''}`,
          GEN_IMAGE_ARGV: argvLog,
          GEN_IMAGE_OUTPUT: output,
        },
      })
      const argv = readFileSync(argvLog, 'utf8').split('\n')

      expect(result.exitCode).toBe(0)
      expect(argv).toContain('sandbox_workspace_write.network_access=true')
    } finally {
      rmSync(fixture, { recursive: true, force: true })
    }
  })



  test('skill and reference files are present', () => {
    for (const path of [
      'skills/image-assets/SKILL.md',
      'skills/image-assets/references/generate.md',
      'skills/image-assets/references/background-removal.md',
      'skills/image-assets/scripts/bg-remove',
    ]) {
      expect(existsSync(join(import.meta.dir, path))).toBe(true)
    }
    expect(statSync(join(import.meta.dir, 'skills/image-assets/scripts/bg-remove')).mode & 0o111).not.toBe(0)
  })

  test('bg-remove produces and preserves real alpha', () => {
    const cli = join(import.meta.dir, 'skills/image-assets/scripts/bg-remove')
    const fixtures = join(import.meta.dir, 'test/fixtures')
    const scratch = mkdtempSync(join(tmpdir(), 'image-gen-bg-remove-'))

    const runFixture = (fixture: string, output: string, extraArgs: string[] = []) => {
      const input = join(scratch, fixture)
      const encoded = readFileSync(join(fixtures, `${fixture}.base64`), 'utf8').trim()
      writeFileSync(input, Buffer.from(encoded, 'base64'))
      const result = Bun.spawnSync([
        cli, input, '-o', output, '--verify-alpha', ...extraArgs,
      ])
      expect(result.exitCode, result.stderr.toString()).toBe(0)

      const alpha = Bun.spawnSync([
        'python3', '-c',
        'from PIL import Image; import sys; a=Image.open(sys.argv[1]).convert("RGBA").getchannel("A"); lo,hi=a.getextrema(); print(f"{lo},{hi}")',
        output,
      ])
      expect(alpha.exitCode, alpha.stderr.toString()).toBe(0)
      expect(alpha.stdout.toString().trim()).toBe('0,255')
    }

    try {
      runFixture(
        'checkerboard-opaque.png',
        join(scratch, 'checkerboard-cutout.png'),
        ['--engine', 'border', '--halo-clean'],
      )
      runFixture(
        'already-transparent.png',
        join(scratch, 'transparent-preserved.png'),
      )
    } finally {
      rmSync(scratch, { recursive: true, force: true })
    }
  }, 60_000)

  test('bg-remove rejects models outside the licensed-local allow-list', () => {
    const cli = join(import.meta.dir, 'skills/image-assets/scripts/bg-remove')
    for (const model of ['withoutbg', 'bria-rmbg', 'isnet-general-use']) {
      const result = Bun.spawnSync([
        cli, 'input.png', '-o', 'output.png', '--model', model,
      ])

      expect(result.exitCode).toBe(2)
      expect(result.stderr.toString()).toContain('invalid choice')
    }
  })

  test('bg-remove Python regression suite passes', () => {
    const result = Bun.spawnSync([
      'python3', join(import.meta.dir, 'test/test_bg_remove.py'),
    ])

    expect(result.exitCode, result.stderr.toString()).toBe(0)
  }, 60_000)


})
