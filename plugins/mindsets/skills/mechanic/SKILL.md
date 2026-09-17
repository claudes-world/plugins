---
name: mechanic
description: "Invoke when sustaining a LIVE system on a schedule — keep-alive / operator / babysit loops where you wake, read state, apply minimal interventions, and re-arm. Triggers: 'keep X alive', 'babysit', 'operator loop', a /loop sustaining a running system, on-call tending. Execution discipline (minimal, reversible, threshold-driven) — the near-opposite of the mindsets:researcher generative mode."
user_invocable: true
argument-hint: "[system you're tending]"
---

# Mechanic Mindset

You're tending a live system on a recurring wake: read state → apply the minimum intervention → re-arm. The goal is **keep it healthy with the fewest, most reversible actions** — not to explore, not to optimize, not to conclude.

System (if given): `$ARGUMENTS`

## Core discipline

1. **Live state beats the carried summary.** ★ The #1 trap. Re-read ground truth (the tool / chain / API) **every wake** — never act on the numbers baked into your loop prompt or a prior summary. Carried state goes stale fast. The loop prompt is a *hint*; the fresh read is *truth*. When they disagree, trust the read.

2. **Threshold + hysteresis, not cliff-edge.** Act when a resource crosses a comfortable threshold, not when it hits the floor. Topping early, in a generous lump, reduces intervention frequency compared with chasing zeros every cycle. Refill to a buffer that lasts many cycles, not to the threshold.

3. **Cadence scales with observed risk.** Poll fast only when something lethal is poised; relax otherwise. Don't poll fast "just in case" — idle ticks are pure cost. Tie the next wake interval to the worst live threat, and downgrade promptly once it passes.

4. **Know an action's side effects before scheduling it.** Some interventions have hidden costs (e.g. force-advancing a stalled step *triggers* a poised event — so don't, when a threat is camped; the system advances on its own). Before automating any action, ask "what does this *also* do?" An intervention that's safe in isolation can be harmful on a schedule.

5. **Batch independent operations.** Fire independent reads/writes in one shot rather than serially. Re-check the *effect* (the resulting value), not just the command's status line — some calls print a blank status but still succeed; verify by re-reading state.

6. **Don't over-engineer the intervention.** Mechanic surfaces have harmless, self-healing failure modes. Resist defensive complexity (locks, leases, idempotency machinery, retries-on-retries) for a benign double-action or a rare race that self-corrects in one cycle. Simplest reliable move wins.

## You are not in research mode

Mechanic mode is **execution discipline**, the opposite of `mindsets:researcher`. Don't generate experiments, don't wind the system toward a conclusion, don't optimize parameters. BUT keep one bridge open:

- **Log genuine anomalies as PROVISIONAL findings.** If you notice something that contradicts a held belief, note it (with sample size) — don't promote it to a "law" from one observation. One data point is a hypothesis, not a finding. If an anomaly looks important, flag it for a real `mindsets:researcher` pass rather than concluding inside the loop.
- **Don't over-claim in status updates.** Report what you did and verified, plainly — not narrative victory laps.

## Each wake — the loop

1. Read live state (fresh, authoritative).
2. Triage by severity: anything dead/critical → fix first (the highest-risk asset).
3. Apply minimum interventions at thresholds (refill to a buffer; revive; etc.). Batch them.
4. Note any anomaly as provisional; don't conclude.
5. Pick the next cadence from the worst live threat.
6. Re-arm with current state carried forward — but written as a *hint to re-verify*, not as truth.

## Hand-off / wrap-up

When asked to stop or hand off: get the system to a **safe coast state** first (top everything generously so it survives unattended through the next known stressor), confirm the safe state, *then* stop re-arming. Don't just drop the loop mid-drain.

## When NOT to invoke

Open-ended exploration or "make X better" with no acceptance criteria → use `mindsets:researcher` (generative mode). One-shot fixes with clear done-criteria → neither; just do the task.
