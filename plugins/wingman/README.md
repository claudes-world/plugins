# Wingman MCP Plugin

Wingman gives Claude Code a named Codex co-researcher: a reusable outside mind for planning, stress-testing, synthesis, and careful technical disagreement.

This plugin is standalone. Install it by itself when you only want the co-researcher workflow, without implementation or reviewer lanes.

## Tools

- `wingman_ask`: create or resume a named Codex wingman session.
- `wingman_sessions`: list or inspect wingman sessions.

## Modes

Fresh sessions use `gpt-6-astra` with `low` reasoning effort by default. `new.effort` still overrides effort. Resume calls continue
the existing Codex session without a model override; this default change does
not rewrite existing session records. After updating the plugin cache, reconnect
the Wingman MCP server and create a fresh named session to pick up the new default.

- `open-question`: explore tradeoffs and answer directly.
- `plan-first-critique`: state a plan, critique it, then recommend.
- `ask-first`: ask clarifying questions when the request is underspecified.
- `stress-test-my-conclusion`: try to break the user's conclusion.
- `synthesize`: compress evidence into a concise recommendation.

## Journaling

Pass `new.journal` when creating a session to append each turn:

```json
{
  "session": "wingman-api-plan",
  "message": "Stress-test this migration plan.",
  "mode": "stress-test-my-conclusion",
  "new": {
    "cwd": "/path/to/worktree",
    "journal": "/path/to/journal.md"
  }
}
```

The journal records timestamp, mode, user message, and Codex reply.

## State

Default state: `~/.local/state/wingman`

Override: `WINGMAN_STATE_DIR=/path/to/state`

Wingman sessions are intentionally separate from Codex implementation sessions, so names never collide across plugins.

Current output sizes are small enough that the server buffers subprocess stdout/stderr before writing logs. That tradeoff is accepted for v1.

Background orphan detection is pid-only in v1 for the shared core runner: a running job is considered orphaned when the recorded runner pid no longer exists. It does not prove process identity across pid reuse.

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
