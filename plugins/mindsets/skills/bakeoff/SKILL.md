---
name: bakeoff
description: "Re-trigger the bake-off mindset whenever you are about to brief several agents/models to produce competing designs, mockups, drafts, or approaches for the human to judge ('bake-off', 'give me N drafts', 'brainstorm interface ideas', 'competition'). The orchestrator's job is to transmit the HUMAN'S brief and materials, trigger high effort, and get out of the way — never to add design philosophies, feature lists, examples, references to existing patterns, or per-entrant 'angles'. Use before writing any entrant prompt; re-invoke if you notice yourself steering. Do NOT use for verification swarms or implementation dispatch, where precise specification is the point."
user_invocable: true
argument-hint: "[what is being baked off]"
---

# Bake-off Mindset — open-ended, undirected, isolated

A bake-off mines for ideas. Every instruction the orchestrator adds beyond the human's brief narrows the field and turns N entrants into N variations of the orchestrator's taste. Your taste enters at **judging**, never at **briefing**.

## The rule

**The prompt is: the human's brief (near-verbatim) + the materials + the effort trigger + the competition framing. Nothing else.**

Do NOT add:
- a design philosophy, "angle", or persona per entrant ("you are the chat-first one", "make it a timeline");
- feature requirements the human did not state (replay, filters, a specific widget) — if the human named a widget, pass it through; do not invent siblings;
- examples, sketches, reference apps, or words that carry a pattern ("like Telegram", "terminal-style", "cards");
- rules distilled from your own analysis (a "viewer contract", a checklist) — hand over the raw schema/data and say the analysis is optional and opinionated;
- a preferred structure for the deliverable beyond the format constraints that make it viewable (self-contained file, size cap, works at the target width).

Do add:
- the human's words for what good looks like ("glanceable", "smooth touch", "connecting lines on a timeline") exactly as said;
- the effort trigger: "plan first, take extra time, think about every piece of good design, go above and beyond, this is a competition";
- permission to exceed: "multiple pages/views welcome if you have more ideas";
- isolation: each entrant works in its own directory and is told not to look at other entrants; separate publish slugs;
- the product-voice rule (no "mock/demo/sample" on the artifact).

## Field shape
- Mix models when asked (e.g. 4 Opus, 1 Sonnet, 2 Codex at xhigh) — model diversity is part of the mining.
- Identical brief to every entrant. If you must differ anything, differ only the codename.
- Run entrants in parallel in PRIVATE, uniquely named directories (e.g. `/tmp/<entrant>-<random>/`) — never the session scratchpad, which is shared by all of one session's subagents. Tell each entrant explicitly.

## Judging
- Collect links + each entrant's own 5-line concept statement; hand ALL to the human at once, unranked, with any open questions the entrants raised.
- Your synthesis ("A's grouping + C's linking") comes only after the human's first reaction, and as a proposal for a revision round — one round, not piecemeal edits.

## Closing rule
If you find yourself writing "make it feel like…" or "include a…" that the human did not say, delete the sentence. The brief is theirs; the ideas are the entrants'; the judgment is the human's.
