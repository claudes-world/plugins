---
name: native-ui-craft
description: "Read before building custom UI, gestures, transitions or list/scroll behaviour on iOS (UIKit, or when SwiftUI is not enough). Covers the techniques behind Telegram iOS's feel: two-phase async layout, UIScrollView as a free physics engine for drag-dismiss, gesture arbitration across a view hierarchy, spring retiming, live portal views, and the discipline for using private API safely. Triggers on: 'iOS', 'UIKit', 'Swift', 'UIScrollView', 'gesture recognizer', 'custom transition', 'interactive dismiss', 'drag to dismiss', 'context menu', 'collection view performance', 'scroll jank', 'CADisplayLink', 'CASpringAnimation', and on native app work."
---


# Native UI craft (iOS)

The iOS-specific mechanics behind the motion and perceived-performance
standards. Sourced from a deep read of Telegram iOS — the
best-executed example available to us.

Source attribution: [Telegram iOS](https://github.com/TelegramMessenger/Telegram-iOS).
These are explanatory notes about its techniques; no application source is bundled.

---

## Two-phase layout: measure anywhere, apply on main

The single most important pattern. Split layout into a pure measurement function
that may run on any thread, returning an immutable layout value **plus a closure**
that commits it on the main thread:

```swift
static func asyncLayout(_ node: Node?) -> (Arguments) -> (Layout, () -> Node)
```

Enforce it structurally, not by convention: make the layout function `static` and
give it a `Weak<Node>` instead of `self`. Layout then *cannot* touch mutable
instance state, because it cannot reach it. Telegram does exactly this in
`ChatMessageBubbleItemNode.beginLayout`.

This is why they wrote their own list view: `UITableView`/`UICollectionView`
measure cells on the main thread inside the scroll callback, which is precisely
the work you need to move off it for heterogeneous self-sizing content. If your
cells are uniform or simple, use UIKit — this pattern is for when they are not.

## UIScrollView as a free physics engine

For anything drag-to-dismiss — sheets, media viewers, panels — do **not** write
drag physics. Put the content in a `UIScrollView` with a synthetic content size
(Telegram uses 3× the screen height) parked at the middle third. Dragging is now
scrolling.

You inherit, for free and matching every other app on the device: Apple's exact
rubber-banding curve, deceleration, and correct handoff when the draggable thing
contains another scroll view.

Then read `contentOffset` for your dismiss decision and `velocity` in
`scrollViewWillEndDragging` for the handoff. Telegram's thresholds: dismiss if
`|velocity| > 1.0` or displacement exceeds `contentSize/12`.

Two refinements they add: subclass and override `setContentOffset(_:animated:)`
to veto UIKit's own scroll-to-visible jumps, and return `true` from
`touchesShouldCancel(in:)` so a drag that starts on a button still pans the sheet.

## Gesture arbitration is a first-class problem

Most "janky" apps are apps with unresolved gesture conflicts. Telegram's approach:

- **Opt-out markers walked up the hierarchy.** At `touchesBegan`, walk from the
  hit-tested view upward looking for properties like
  `disablesInteractiveTransitionGestureRecognizer`. This is how swipe-back works
  anywhere in a chat but never fights a horizontally-scrolling sticker row.
- **Direction as an OptionSet** distinguishing edge from centre, per axis, with a
  configurable edge width — not a single boolean.
- **Aggressive cancellation on activation.** When the context gesture commits, it
  recurses the window failing competing tap recognizers, walks *up* the superview
  chain cancelling parent gestures, cancels list selection and un-highlights
  buttons. This is why the menu never leaves a stuck highlight behind.
- **Guard the system edges.** Fail your own recognizer within ~8pt of the screen
  edge so it never steals the system back gesture.

## Spring retiming — decouple feel from duration

```swift
animation.duration = animation.settlingDuration
animation.speed = Float(animation.duration / targetDuration)
```

Never let a spring run its natural settling duration. Keep the
mass/stiffness/damping ratio you tuned, and still hit the duration the design
asks for. Without this, springs cannot be scheduled against anything else.

Telegram's tuned constants, as starting points: default spring mass 3.0 /
stiffness 1000 / damping 500; their iOS-26-matching spring is mass 1.0 /
stiffness 555.027 / damping 47.118; the bouncy variant is mass 5.0 / stiffness
900 / damping 88, with heavier damping (104, 180) for larger surfaces.

## One display link for the whole app

Do not create a `CADisplayLink` per animator. Run a single shared driver that
takes the max requested frame rate across active clients, creates and destroys
the one link, and auto-pauses on background. A 30fps decorative animation and a
120fps gesture then coexist correctly.

Set `preferredFrameRateRange` per animation. Telegram pins *opacity* animations
to 60fps while giving position the full 120 — alpha does not need ProMotion, and
this is a real battery saving.

## Make hand-driven and CoreAnimation curves identical

If you drive anything yourself (display link, scroll offset, interpolated
heights) it must follow the *exact* curve of the CoreAnimation animations running
beside it, or the frame will not cohere — things visibly "swim". Telegram solves
this by reaching `-[CASpringAnimation _solveForInput:]` through the ObjC runtime
and using it as their CPU-side interpolator.

Also multiply `UIAnimationDragCoefficient()` into every duration in hand-rolled
animators, so the simulator's slow-motion still works. It is the only practical
way to actually inspect a 300ms transition.

## Live mirrors instead of snapshots

For lifted previews (context menus, drag), a snapshot freezes video and animation.
`_UIPortalView` mirrors another layer tree live, so a playing video keeps playing
in the preview. Hand off from the portal to the real node when the transition
settles.

## Blur is expensive; render it small

Below-system-material fallbacks should blur at reduced scale (Telegram uses 0.3×
on @3× devices) and let the compositor upscale. It is blurred; nobody can tell.

## Private API discipline

If you must, do it the way they do:
- **One module** holds every private-API touchpoint, nothing scattered.
- Each is behind a runtime availability check **with a public fallback**.
- Class names assembled from string arrays to avoid static detection.
- Never let private API be load-bearing for correctness — only for polish.

Note this is a survivability pattern for a fork, not a recommendation to reach
for private API. Everything above this section is achievable without any.

## When to write your own vs. use the framework

Write your own when: cells are heterogeneous and self-sizing and you need
off-main measurement; you need interruptible, velocity-aware, retargetable
transitions; you need layout features the text/layout system genuinely cannot
express (Telegram's message text wraps *around* the timestamp — a per-line
exclusion rect no standard text engine offers).

Otherwise use the framework. Telegram's approach is justified by a chat list at
120Hz over a 100k-message history; most screens are not that.

---

Related: `motion` (the animation guidance), `perceived-performance`,
and the upstream Telegram iOS source linked above.
