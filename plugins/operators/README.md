# Operators MCP Plugin

Policy-free dispatch tools for teammate CLIs: Codex for coding, Gemini through `agy`, and verified Cursor models.

This server dispatches explicit requests. Apply your own review and service-use policy.

## Tools

- `codex_plan`: Stage 1 plan-only Codex dispatch. Registers a named implementation session.
- `codex_implement`: resume the named session for Stage 2/4 implementation.
- `codex_critique`: resume the named session for Stage 3/5 self-review.
- `codex_exec`: one-shot fresh Codex call for quick work that does not need a registry entry.
- `codex_result`: fetch a background Codex job.
- `agy_ask`: one-shot Gemini-only analysis via `agy`.
- `cursor_ask`: one-shot Cursor analysis for the configured GPT/Codex and Opus 4.6 allow-list.
- `operator_sessions`: list or inspect Codex implementation sessions.

## Codex Steering Pattern

### Staged work

Use the staged tools for non-trivial implementation:

1. `codex_plan`: make Codex inspect and plan without editing.
2. `codex_implement`: approve/refine the plan and let it edit.
3. `codex_critique`: ask Codex what is still missing.
4. `codex_implement`: apply accepted follow-up work.
5. `codex_critique`: ask once more, then stop when the returns diminish.

Use `codex_exec` for short one-shot analysis or mechanical dispatches where session continuity does not matter. Because it does not write a registry entry, a successful `codex_exec` does not require Codex to print a session UUID; when a UUID is present, the response metadata includes `codex_session_id`. Pass `cwd` explicitly; one-shot tools never inherit the server process directory.

Codex briefs and directives are always sent via stdin. Resume calls use the registered session cwd and put options before `resume`:

```text
codex exec --skip-git-repo-check --sandbox <mode> -c approval_policy=never resume <SID>
```

## Routing Policy

`agy` is Gemini-only. Non-Gemini model requests are rejected. `agy_ask` accepts optional `effort`: `gemini-3.1-pro` allows `low`/`high`, while `gemini-3.5-flash` allows `low`/`medium`/`high`. Both default to `high` when omitted.

`cursor` is GPT/Codex + Opus 4.6 only. Cursor CLI calls are expensive; use them for deliberate dispatches, not loops.

`codex_exec`, `agy_ask`, and `cursor_ask` require `cwd` on every call.

The cursor model allow-list in `config.json` was verified with `cursor-agent models` on 2026-07-02. Re-verify after Cursor updates.

## State

Default state: `~/.local/state/operators`

Override: `OPERATORS_STATE_DIR=/path/to/state`

Full logs live under `logs/`; tool responses return capped tails.

Current output sizes are small enough that the server buffers subprocess stdout/stderr before writing logs. That tradeoff is accepted for v1.

Background orphan detection is pid-only in v1: `codex_result` marks a running job orphaned when the recorded runner pid no longer exists. It does not prove process identity across pid reuse.

## Manual Smoke

`./smoke-stdio.sh` launches `bun server.bundle.js` without the test-only transport and checks `initialize`, `tools/list`, and a trivial `tools/call` over stdio. It is standalone and not wired into the harness; it may not run in this sandbox because of Bun stdin limitations.

## Standalone use and license

This directory is an independent plugin root. Enable it in your plugin host.
Owned code and content are MIT licensed; third-party terms remain in
`THIRD_PARTY_NOTICES.md`. Provider requirements are declared in `providers.json`.

Bun is required. The checked-in `server.bundle.js` includes the locked MCP SDK;
`bun run start` and `bash test-harness.sh` work without installing dependencies.
For development, run `bun install --frozen-lockfile` then `bun run build`.
`bun test` runs any package-local unit tests. No provider is called at startup.
External CLI authentication and billing are managed by the host; this plugin
neither provisions credentials nor silently switches providers. Tests use local
stubs only. Missing CLI calls return an error while session inspection still works.

The optional `agy` adapter must accept `--model MODEL --effort EFFORT`, optional
`--add-dir PATH` arguments, `--sandbox --dangerously-skip-permissions`, and `-p PROMPT`, and return analysis on stdout.
It is user-supplied: no private adapter repository or host installation is needed
for Codex, Cursor or session-listing tools. `OPERATORS_AGY_BIN` can select an
implementation of that contract. Cursor similarly uses `OPERATORS_CURSOR_BIN`;
Codex uses `OPERATORS_CODEX_BIN`. These optional accounts may incur charges.
