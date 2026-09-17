---
name: perceived-performance
description: "Read when an interface feels slow, laggy or unresponsive, or before building anything where responsiveness is the point — chat, feeds, media galleries, editors, dashboards. Covers the difference between being fast and feeling fast: instant acknowledgement, optimistic UI, placeholders that carry real information, removing input latency, and doing expensive work off the critical path. Triggers on: 'feels slow', 'laggy', 'janky', 'unresponsive', 'perceived performance', 'loading state', 'skeleton', 'spinner', 'optimistic update', 'why does this feel slow', 'reduce latency', 'first paint', 'time to interactive'."
---

# Perceived performance

Users do not experience milliseconds. They experience *acknowledgement*,
*continuity* and *predictability*. An app that responds in 16ms and finishes in
2s feels faster than one that responds in 400ms and finishes in 800ms.

Derived from a deep read of the Telegram iOS source. Applies to web
and native alike.

---

## Acknowledge in the same frame as the input

Every touch, click or keypress must produce a visible change immediately —
before any work starts, before any network call. The acknowledgement is a
separate concern from the result.

Concretely, kill input latency you did not know you had:
- On iOS, scroll views delay touches by ~150ms to disambiguate scrolling from
  tapping. Telegram turns this off everywhere (`delaysContentTouches = false`)
  so buttons highlight the instant they are touched.
- On the web, the equivalents are `touch-action`, avoiding click delay, and
  never gating the pressed state behind a state round trip.
- Prepare expensive feedback machinery at gesture *begin*, not at commit. Telegram
  spins up the haptic engine the moment a finger lands, before it knows whether
  the gesture will commit, so the haptic fires with no lag.

## Show the press building, not just the result

Long-press, hold-to-record and similar should expose a *continuous progress*
signal from the moment contact starts — the target visibly responds throughout
the hold. A boolean that fires after 500ms feels like an ambush; a continuous
one feels like a mechanism.

## Optimistic by default

Render the user's action as done immediately, reconcile with the server later,
and design the failure path explicitly (a distinct visual state and a retry
affordance — not a silent revert, and not a modal error).

The message you sent should appear in the list instantly with a pending
indicator. This is table stakes in messaging and underused everywhere else.

## Placeholders should carry information, not just occupy space

A grey box tells the user nothing. Telegram ships a ~30-byte thumbnail with every
photo and reconstructs a blurred, correctly-coloured preview from it — so the
placeholder already has the *shape and colour* of the real image, before any
network request. The transition to the real image is then barely perceptible.

Generalize: derive the placeholder from real data you already have. Dominant
colour, aspect ratio, first line of text, item count. A skeleton that matches the
final layout's dimensions prevents the reflow jump; one that matches its content
prevents the perceptual jump too.

## Get expensive work off the critical path

- **Measure/layout off the interaction thread** where the platform allows it.
  The reason Telegram wrote its own list view is that UIKit measures cells on the
  main thread inside the scroll callback. On the web the analogue is avoiding
  forced synchronous layout in scroll handlers, and doing heavy work in a worker.
- **Pre-render expensive content once into a cheap replayable form.** Telegram
  renders vector stickers once, converts to a compact colour format, compresses,
  memory-maps the result, and plays back by decompressing — no vector
  rasterization at playback. Web analogue: pre-rasterize, cache, and replay
  rather than re-computing per frame.
- **Reuse buffers.** Allocate the scratch space once and reuse it per frame;
  per-frame allocation is a common source of jank.
- **Decide async-vs-sync per element.** Async drawing has dispatch overhead; for
  small static content it costs more than it saves. Telegram opts *out* of async
  drawing in over a thousand places. Blanket policies are wrong in both
  directions.

## Prefetch what the user is about to want

Preload a window around what is visible, not only what is visible. Telegram uses
a 500pt preload inset versus a 20pt one when prefetching is enabled. For media,
fetch the next item in the sequence. The cost is bandwidth; the benefit is that
the common path never waits.

## Never let the container resize under the user

Reserve space for content that is still loading. Growing content sizes, late
image dimensions and post-hoc font swaps all cause the layout to jump, which is
perceived as slowness *and* as sloppiness.

## Keep identity stable across the optimistic→confirmed swap

The most valuable single detail in Telegram's send path. A pending message is
stored under a local id; when the server confirms, the id changes — but a separate
**stable identity** is carried over, and the list diffs on that.

So confirmation is an *in-place update of the existing row*: the clock becomes a
checkmark and nothing moves. Delete-the-local-row + insert-the-real-row produces a
delete animation and an insert animation at exactly the moment the user is looking
at it.

Same rule on failure: keep the row, keep the identity, change the state. A failed
action must never be a disappearance.

Generalize: whenever a provisional object is replaced by a canonical one, give the
UI an identity that spans both.

## Deliberate delay is an optimization

Counter-intuitive, and used everywhere in Telegram. A small, bounded wait in a rare
case eliminates work in the common case:

- **2 seconds** before escalating a detected gap in the update stream to a full
  resync — because the usual cause is packet reordering, not a real gap.
- **300ms** debounce before starting a prefetch, so an item that scrolls past in a
  ranking never fires a request.
- **500ms** grace before cancelling an in-flight fetch the user scrolled away from —
  the "overshot and coming back" window.
- **1 second** grace before discarding an orphaned upload, so closing and reopening
  a picker doesn't throw away an 80%-complete transfer.
- **10 seconds** batching of cache access-time writes, turning hundreds of syscalls
  per second during a scroll into one burst.
- **20 minutes** before tearing down an idle connection, because the handshake costs
  far more than the idle socket.

Before adding a cancel-immediately or retry-immediately path, ask what the delay
would cost in the rare case versus what it saves in the common one.

## Model absence explicitly

Telegram's message store does not represent "we have messages 500–600 and nothing
else". It represents *known-unknown ranges* — a new chat starts as one gap covering
everything, and every fetch subtracts from it.

This is what lets the UI render partial data immediately and correctly: it can tell
"this conversation has no older messages" from "we haven't looked yet", show a
loading edge only where one belongs, and know exactly what to request. A model with
only present/absent has to guess, and guesses wrong in both directions.

## Race, don't sequence — then remember the winner

For anything with multiple possible routes (endpoints, transports, mirrors), issue
them concurrently and take the first success, rather than trying each with a
timeout. Sequential worst case is N × timeout; racing is one round trip of the
fastest reachable path.

Then **persist which ones worked**. Telegram records per-address success and failure
timestamps to the keychain, and skips an entire address family that hasn't worked
recently — so the second cold start is measurably faster than the first.

And consider a two-phase upgrade: accept the degraded route that answered first, but
keep racing in the background and switch up if a better one appears. Otherwise one
bad network moment pins you to the slow path for the session.

## Prefetch what they will land on, not what is newest

For an unopened item, work out what the user's *first screenful* will actually be
and warm that. Telegram anchors its background prefetch on your last-read marker
and preloads the first few media items after it — not the most recent messages,
which is what a naive implementation would fetch and which you may never see.

## Generate skeletons from the real component

Do not hand-write skeleton geometry. Construct the actual component with placeholder
data, run the real layout, read back the resulting rects, and mask from those.

The skeleton is then guaranteed to match the content that replaces it under every
font size, theme and locale — and it cannot drift when the component changes. Every
hardcoded skeleton eventually disagrees with its content.

## Checklist

1. Does something visible change in the first frame after input?
2. Is there input latency you inherited from the platform's defaults?
3. Is the action rendered optimistically, with an explicit failure state?
4. Do placeholders carry the real thing's shape, colour and size?
5. Is anything expensive running on the thread that handles interaction?
6. Are you re-computing per frame what could be computed once and replayed?
7. Does the layout ever jump when content arrives?

---

Related: `motion` (the animation guidance), `native-ui-craft` (iOS mechanics).
