---
name: wingman
description: "Re-trigger best practices for collaborating with a CODEX CO-RESEARCHER ('wingman') during research/exploration — codex as a thinking partner that critiques, stress-tests, designs experiments, and synthesizes, NOT as an implementer. Proactively invoke whenever you'll have a codex session open alongside an open-ended experiment, want a second model to challenge your conclusions, or are about to write a big one-shot codex brief (it'll remind you to go multi-turn instead). Part of the mindsets family (mindsets:researcher, mindsets:mechanic). Do NOT use for codex-as-implementer (writing/refactoring code)."
user_invocable: true
argument-hint: "[topic / what you're researching together]"
---

# Wingman Mindset — collaborating with a codex co-researcher

A codex session run *alongside* your research as a thinking partner: it critiques designs, catches your over-claims, proposes experiments, and synthesizes. This is **codex-as-co-researcher**, distinct from codex-as-coder.

Topic (if given): `$ARGUMENTS`

## Two habits that matter most ★

**1. Frequent short multi-turn dialog — NOT one giant brief.**
The instinct is to write a huge single-turn message dumping all context + asking everything at once. Resist it. Instead, **resume the same codex session and trade short focused turns**: state one thing, let codex react, respond to its reaction, branch. Why it's better:
- Back-and-forth surfaces more than a monologue — codex's reply to turn 1 reshapes what you ask in turn 2 (the same generative loop that makes research work).
- Short turns keep codex's working context tight and on-topic; a wall-of-text brief buries the actual question and invites generic answers.
- You catch a wrong turn early instead of after a 2000-token response built on a bad premise.
Treat it like talking to a sharp colleague, not filing a ticket. One idea per turn; iterate.
Ask the wingman to keep replies brief so the dialog stays focused.

**2. Journal frequently — append per exchange, not one dump at the end.**
Keep a co-researcher journal open and **append as you go** — after each notable exchange, not in a single retrospective write-up (which loses detail and tempts hindsight-shaping). A useful per-session header schema: date, codex_mode (C/R), reasoning level, n_sprints, n_contributions_codex_caught, n_hallucinations_or_wrong, n_decisions_changed_by_codex, n_exploration_loops, prompting_styles_used, verdict. Running notes below it. Frequent appends are what make weeks of runs aggregatable.

## Prompting modes (name the mode in each turn)

- **open-question** — "what do you make of X?" Best for early divergence.
- **plan-first-critique** — codex drafts an approach, you critique, it revises.
- **ask-first** — codex must ask clarifying questions before answering (counters premature answers).
- **stress-test-my-conclusion** ★ — "I concluded X; try to break it." *Highest-value mode* and the easiest to skip solo. This is the honesty backstop that catches over-claims (e.g. promoting a one-sample observation to a law). Run a conclusion through this BEFORE you journal it as a finding.
- **synthesize** — at a milestone, have codex compress the session into findings. Strong at end-of-run synthesis.

Alternate deliberately; don't get stuck in open-question mode.

## Continuous vs Reset (a running experiment worth keeping)

**Mode C** = one session resumed all night (deep cross-sprint context, risks anchoring); **Mode R** = fresh session at each context reset (no anchoring, but re-briefing cost). Alternate by date parity and log which mode + its verdict each session, so a multi-week comparison stays aggregatable.

## Dispatch mechanics (so codex actually runs)

This workflow optionally uses a host-installed Codex CLI and account. If either
is unavailable, report that limitation and use the other local mindset modes;
keep solo research conclusions provisional. Do not substitute a paid API.


- **stdin-pipe, never heredoc-as-argument.** `cat brief.md | codex exec … resume <session-id> -` — heredoc-as-arg silently hangs codex waiting on stdin. Options go BEFORE `resume`.
- **cwd quirk:** `codex exec resume` uses the CURRENT shell cwd, not the original Stage-1 `-C`. `cd <worktree>` first.
- **sandbox:** co-research is usually read/think → `--sandbox workspace-write` (or `read-only`) is fine; use `danger-full-access` only if a turn needs network/RPC.
- **reasoning level:** low/medium is plenty for dialog; reserve high/xhigh for hard synthesis. Verify via the chrome header "reasoning effort:".

## When NOT to use

- Codex writing/refactoring code → use a codex-as-implementer pattern instead (multi-stage plan→implement→critique→improve steering).
- Solo non-research work, or when a single quick question genuinely needs no back-and-forth.

Companion: `mindsets:researcher` (the research mindset this supports), `mindsets:mechanic` (its execution-discipline counterpart).
