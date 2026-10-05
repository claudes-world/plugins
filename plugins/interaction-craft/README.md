# interaction-craft

How interfaces earn their feel — the motion guidance (stagger, never synchronize), perceived-performance doctrine, and the iOS mechanics behind both. Distilled from a deep read of the Telegram iOS source.

Included skills: motion, perceived-performance, native-ui-craft, screen-design. Enable the plugin in a skill-capable host; no MCP server or executable is required.

## Screen design

`screen-design` covers how a screen reads as design, Jetpack Compose first, web second, with SwiftUI
notes: proportional placement and edge anchoring, spacing rhythm, optical alignment, concentric radii,
surfaces, typography (line breaks, tabular figures, monospace identifiers), colour and contrast,
touch targets, UI wording, icons, press feedback and when not to animate. Every layout ask becomes
numeric targets, and every design round ships an old-versus-new render pair. Before designing or
reviewing, the skill reads the project's design profile (`**/design/DESIGN-PROFILE.md`) and tokens.
Reference files: `compose.md`, `web.md`, `typography.md`, `surfaces-and-colour.md`,
`review-checklist.md`.

Included agents:

- `design-planner` turns a design ask into a plan before any build: numeric targets with tokens, layout structure, type roles, states and renders to produce, motion decisions, at most three open decisions, and a handoff block for the reviewer. Read-only.
- `design-reviewer` reviews renders and the diff after a build, given only the plan's numeric targets: it opens every image, compares old with new, measures positions with PIL, walks the review checklist and returns a Block or Approve verdict. Read-only.

## Standalone use and license

This directory is an independent plugin root. Enable it in your plugin host.
Owned code and content are MIT licensed; third-party terms remain in
`THIRD_PARTY_NOTICES.md`. Provider requirements are declared in `providers.json`.

Validate the installed skill/agent entrypoints with `python3 test_package.py`.
