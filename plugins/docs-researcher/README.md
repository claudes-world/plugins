# docs-researcher plugin

Version-pinned library docs on demand.

One sandboxed researcher subagent (`agents/docs-researcher.md`) wired to
[Context7](https://github.com/upstash/context7) — Upstash's documentation MCP
(`resolve-library-id` / `query-docs`, dense version-pinned snippets for
popular OSS frameworks) — with WebSearch fallback.

## Why not plain WebSearch

- **Version-pinned accuracy** — the failure class this kills: coding against
  training-data recall or a stale third-party SEO page.
- **Dense pre-chunked snippets** — cheaper than crawling doc sites.
- **Works where doc sites 403 automated fetches.**

Honest limits: Context7 covers OSS library docs, NOT product help centers or
pricing pages — that class of question belongs to a general web-research
agent (whichever one the calling loadout carries; none ships in this repo).
The agent def enforces this boundary and the injection-containment doctrine
(fetched docs are untrusted data).

## Scoping (the point of this being its own plugin)

Context7 is registered when this plugin is enabled. The researcher agent
allowlists its tools; the host controls tool visibility outside that agent.
Requires Node.js and npm/npx on PATH. If the CLI or service is unavailable,
the agent reports reduced fidelity and uses host WebSearch.

The server is stdio `npx -y @upstash/context7-mcp@3.2.3` (version-pinned; bump deliberately) (no API key required for
anonymous use; rate-limited — an `CONTEXT7_API_KEY` env can be added to
`.mcp.json` later if limits bite).

## Tool-name compatibility

`agents/docs-researcher.md` allowlists both the bare Context7 tool names and
the plugin-qualified names observed for plugin-scoped MCP servers:
`mcp__plugin_docs-researcher_context7__resolve-library-id` and
`mcp__plugin_docs-researcher_context7__query-docs`. If neither form is
reachable after ToolSearch, the agent reports that Context7 is unavailable
and that its WebSearch fallback has reduced doc-version fidelity.

## Standalone use and license

This directory is an independent plugin root. Enable it in your plugin host.
Owned code and content are MIT licensed; third-party terms remain in
`THIRD_PARTY_NOTICES.md`. Provider requirements are declared in `providers.json`.

Validate the installed skill/agent entrypoints with `python3 test_package.py`.

The pinned 3.2.3 package exports `resolve-library-id` and `query-docs`; the
agent uses those names even though some upstream README examples retain older
`get-library-docs` wording.
