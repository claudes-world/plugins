---
name: motion
description: "MUST read before writing ANY animation or transition — CSS, JS, SwiftUI/UIKit, Remotion/video, Framer Motion, GSAP, canvas, or hand-driven. Covers the motion guidance for combining animations (stagger, never synchronize), spring feel vs timing, additive animation, velocity handoff from gesture to animation, and interruptibility. Triggers on: 'animate', 'animation', 'transition', 'fade in', 'slide in', 'easing', 'spring', 'duration', 'keyframes', 'motion design', 'micro-interaction', 'make it feel smoother', 'the animation looks janky', and on building any transition between two UI states."
---


# Motion — motion guidance

Platform-agnostic. These are properties of human perception, not of iOS.

Derived from a deep read of the Telegram iOS source, which is the
best-tuned motion implementation we have studied. The iOS-specific mechanics
live in `native-ui-craft`; what follows applies to web, video and native alike.

---

## THE RULE: never give two things in one transition the same duration

When several properties or elements animate
together, stagger them. Uniform durations read as mechanical; the eye sees a
rigid block move rather than a thing arriving.

Specifically:

- **Lead with opacity, follow with motion.** A fade that starts ~40–60ms ahead
  of the movement eases the motion in perceptually and hides the moment where
  two shapes don't quite match.
- **Animate different properties over different spans.** In Telegram's
  chat→fullscreen image transition, no two durations match: outgoing alpha
  0.20s, incoming alpha 0.10s, position 0.21s, transform 0.25s, bounds 0.25s.
- **Stagger siblings.** Items in a list or grid should arrive on a short
  cascade (~20–40ms apart), not as one wall.
- **Animate `bounds`/size separately from position** when the crop or aspect
  changes. Morphing the frame and moving it on the same timeline looks wrong;
  offsetting them hides the mismatch.

If you are about to write two animations with identical durations and delays,
that is the signal to apply this rule.

## Feel and timing are separate knobs

A spring's *feel* is its mass/stiffness/damping ratio. Its *duration* is how long
you want it to take. Do not conflate them: pick the feel you want, then retime it
to the duration the design calls for. (Telegram literally rewrites a spring's
`duration` to its natural settling time and then scales `speed` to hit the
target — see `native-ui-craft`.)

Practical consequences:
- Don't reach for a longer duration when what you want is more damping.
- Don't tune a spring by lengthening it until it stops overshooting.
- Reuse a small vocabulary of named curves across a product. Two or three
  springs plus one ease is usually the whole system.

## Animate additively: set the final state, animate the offset

Set the model/layout to its **final value immediately**, then animate a purely
visual offset from `-Δ` back to `0`.

Why it matters: the application's state is correct for the entire animation. Hit
testing, layout, scroll position and any code reading the value all see the truth.
And because the animation is decoration rather than state, it can be interrupted,
retargeted, or have another animation stacked on top without recomputing anything.

The alternative — animating the real value from A to B — means every reader of
that value sees a lie for 400ms, and interrupting mid-flight requires unwinding.

## Always resume from the *visual* position, never the model position

When you retarget something that is already moving, read where it currently
*appears* (the presentation/computed value) and animate from there. Starting the
new animation from the model's target causes the visible jump that reads as
"snappy" or "cheap".

This single distinction is most of the difference between a UI that feels
physical and one that feels like state changes with decoration.

## Hand off velocity from gesture to animation

When a drag ends, the animation must start at the speed the finger was moving.
Normalize the gesture velocity into the animation's unit space and inject it as
the spring's initial velocity:

```
initialVelocity = gestureVelocity / remainingDistance
```

Without this there is a visible hitch at the moment of release — the object
stops dead and then re-accelerates. With it, the object simply continues.

Corollary: decide *whether* to complete or cancel using velocity as well as
position. "Past 20% **or** moving faster than X" beats a pure position threshold —
a fast flick should commit even if it barely moved.

## Everything a finger touched must be interruptible

If the user can start it with a gesture, they must be able to grab it again
mid-flight. Present a sheet with user interaction still enabled during the
animation. This falls out of additive animation plus presentation-layer
retargeting; it is very hard to bolt on afterwards.

## Phase-lock repeating animations

If several elements run the same looping animation — spinners, shimmers, pulsing
dots — they must be **in phase**, or the screen looks broken rather than busy.

Elements are created at different moments, so a naive "start now" loop leaves them
visibly out of sync. Anchor the loop to an absolute point on a shared clock instead
of to creation time, so phase is `(now − anchor) mod duration` for every element
regardless of when it appeared. Telegram does this with a single constant
(`beginTime = 1.0`) at ~20 sites; on the web the equivalent is a negative
`animation-delay` derived from a shared epoch.

Six pending-message spinners turning in lockstep is a one-line change and reads as
a system. Six spinners at random phases reads as a bug.

## When you interrupt an animation, start from what is on screen

Two applications of the same idea:
- Re-target position/size from the presentation value (above).
- Fade **from the current opacity**, not from 1.0. A badge that changes twice in
  quick succession will visibly flash back to full before fading if you don't.

Also: if you kill a repeating animation mid-cycle, read its current offset first and
replay that residual back to zero, or the element teleports by whatever the loop's
amplitude was.

## Snap positions to whole device pixels

Interpolated sub-pixel positions make text shimmer during movement. Round every
animated position to the device pixel grid. Cheap, and the difference is visible
on any screen with text in motion.

## Respect the platform's motion settings

Honour reduce-motion. The correct response is usually to replace movement with a
cross-fade, not to disable the transition entirely — an instant cut loses the
causal information the animation was carrying.

## Durations — starting points, not laws

- Micro-feedback (button press, toggle): 100–150ms
- Element enter/exit, small: 200–250ms
- Screen or sheet transition: 300–450ms
- Anything over ~500ms needs a reason; the user is now waiting

Gesture-driven completions should derive duration from remaining distance ÷
velocity, clamped (Telegram clamps to 50–200ms), not use a fixed number — a
flick that is nearly done should finish fast.

## Checklist before shipping a transition

1. Do any two properties share a duration? Stagger them.
2. Does opacity lead the motion?
3. Is the model at its final value for the whole animation?
4. If interrupted mid-flight, does it resume from the visual position?
5. If gesture-driven, is velocity carried into the animation?
6. Are positions pixel-snapped?
7. Does it degrade sensibly under reduce-motion?

---

Related: `perceived-performance` (making it feel fast rather than smooth),
`native-ui-craft` (the iOS mechanics behind all of this).
