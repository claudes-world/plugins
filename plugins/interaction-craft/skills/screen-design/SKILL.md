---
name: screen-design
description: "MUST read before designing, laying out, restyling or reviewing any screen, component or visual change, before planning numeric layout targets, and before reviewing renders or screenshots. Covers how a screen reads as design: proportional placement and edge anchoring, spacing rhythm, optical alignment, concentric radii, surfaces (shadow for elevation, border for structure), typography (hierarchy, line length, line breaks and wrapping, tabular figures, monospace for versions and identifiers), colour and contrast roles, touch targets, UI wording, icons, press feedback and when not to animate. Jetpack Compose first, web second, SwiftUI notes. Triggers on: 'design', 'layout', 'restyle', 'redesign', 'move it up', 'move it down', 'make it bigger', 'spacing', 'padding', 'alignment', 'typography', 'font', 'contrast', 'dark mode', 'touch target', 'design review', 'review the render', 'review the screenshot', 'looks off', 'polish', 'Compose UI', 'new screen'."
---

# Screen design

How a screen reads to the person holding it: where things sit, how they group, how text breaks
and what the words say. Rules carry exact numbers and a one-line reason. Motion between states
belongs to `motion`; this skill covers the static screen, press feedback, and when not to animate.

Platform recipes: [compose.md](compose.md) (Jetpack Compose, with SwiftUI equivalents) and
[web.md](web.md). Depth: [typography.md](typography.md), [surfaces-and-colour.md](surfaces-and-colour.md).
Reviewers walk [review-checklist.md](review-checklist.md).

## Project profile first

1. Before designing or reviewing, find and read the project's design profile and tokens: Glob
   `**/design/DESIGN-PROFILE.md`, `**/DESIGN-TOKENS.md`, and the theme source (Compose `ui/theme/*.kt`,
   CSS custom properties, Tailwind config, SwiftUI `Theme.swift` or asset catalog). Read the brand files the profile names.
2. Use only token values that exist. A value the system lacks is a proposal and is named as one:
   "Proposed token `space4_5` = 18 dp; no existing step between `space4` 16 and `space5` 20 fits because …".
3. Where a project token differs from a number in this skill, the project wins. Report the difference once; do not override it.
4. Product vocabulary rules in the profile are binding on every string you write or approve.

## Numeric targets

Every layout ask becomes measurable targets before any code changes.

- Translate words into numbers: "move the logo down" becomes "logo centre from 17% to 28% of screen height".
- Positions are fractions of the screen dimension (they hold across device sizes); gaps and sizes are dp/px; every value names its token.
- Say what the fraction is measured against: full window height or safe height (between the status bar and the navigation bar).
- A change the requester asked to see must be visible: at least 4% of screen height (37 dp on a 915 dp screen). 16 dp was invisible in practice (example 1).
- Each target carries a tolerance: default 1% of the screen dimension for fractions, 2 dp for fixed values.
- Write targets as a table: element | property | current | target | token. "Current" is measured from a render, not read from intent.
- Every round ships an old-versus-new render pair of the same state at the same size.
- Where the platform allows, encode each target as a test (test tag plus bounds in root, see [compose.md](compose.md#numeric-targets-as-tests)).

## Layout

- **Anchor every element to one edge or a fraction.** Footers and docks to the bottom inset, headers to the top inset, hero content to a fraction of height. An element anchored to the wrong edge drifts when screen height changes.
- **Place hero content proportionally, not with a fixed top padding.** A fixed 120 dp top lands at 17% of a 700 dp screen and 13% of a 915 dp one.
- **One spacing scale.** Every gap is a step of a 4 dp or 8 dp base (or the project's base). Off-scale gaps read as mistakes.
- **Group with space before lines.** Gap between groups ≥ 2× gap within a group (8 dp within, 16 dp or more between). Then filled backgrounds; divider lines last. Equal gaps make groups unreadable.
- **Shared edges.** One leading edge per column; a 2 dp offset from a shared edge reads as an error.
- **Gutter.** 16–20 dp each side on phones; full-width buttons sit inside it. Text against the screen edge is hard to read and collides with curved corners.
- **Content bleeds, controls stay inside the safe area.** Backgrounds and media may reach the edges; text and controls never sit under the status bar, cutout or gesture area.
- **Order by importance.** The fact the person came for sits top and leading; one filled primary action per screen.
- **Controls look like controls.** Every interactive element has a fill, a border or a fixed control position; a control styled as body text is not found.
- **Space between targets.** 12 dp between adjacent filled or bordered controls, 24 dp around borderless icon or text controls; hit areas never overlap.
- **Optical alignment.** Button with a trailing icon: icon-side padding = text-side padding − 2 dp. Play triangle: shift 2 dp toward the point. Asymmetric icons: fix the vector, not the layout. Geometric centring of uneven shapes looks off-centre.
- **Concentric radii.** Outer radius = inner radius + padding (12 dp inner + 8 dp padding = 20 dp outer). Past 24 dp of padding, choose each radius independently. Equal radii on nested shapes make the gap narrower at the corners than along the sides.

## Surfaces

- **Shadow for elevation, border for structure.** Shadow for things above the page (sheets, menus, toasts, a dragged item); 1 dp border for cards in a flat system, dividers, inputs, selected and focus states. Never both for the same purpose on one surface.
- **Dark theme separates with a lighter surface step or a 1 dp ring** at 8% white (13% on hover); shadows do not show on dark backgrounds.
- **Images get a 1 dp outline inside the edge**: 10% black on light, 10% white on dark, never a tinted neutral, which takes on the surface colour as a cast along the edge.
- Details and dark-theme recipes: [surfaces-and-colour.md](surfaces-and-colour.md).

## Typography

- **Hierarchy from a fixed role scale.** Each role is size + weight + line height + tracking; one display-size number per screen; heading sizes descend with level. One-off sizes break hierarchy.
- **Line height.** Headings 1.1–1.2, body 1.4–1.6; anything that wraps to 3 lines or more ≥ 1.4.
- **Weight floor.** 400 or heavier below 18 sp; thin weights vanish at text sizes.
- **Line length.** Paragraphs 45–75 characters per line; longer lines lose the reader at the line start.
- **Wrapping is a decision.** Labels, buttons, chips, tags, footers, versions and identifiers are one line at the smallest supported width and the largest font scale. When two pieces of information do not fit one line, use two explicit rows; never let a line break fall where it lands.
- **Never break inside a unit of meaning**: a value and its unit, anything in brackets, a version string, a name. A break there reads as two separate statements.
- **No orphans.** A heading or short description never ends with one short word alone on its last line.
- **Tabular figures** on every number that changes or lines up in a column (`tnum`); proportional digits shift the layout as values update.
- **Monospace for versions, build numbers, IDs and codes**, set smaller or lighter than the statement they accompany; people compare them character by character.
- **Truncate only with an ellipsis and a path to the full value.** Never truncate money or a name the person must verify.
- Size floors: 12 sp minimum, body 15–17 sp on phones, web inputs 16 px. Details: [typography.md](typography.md).

## Colour and contrast

- **Role tokens only.** Text primary and secondary, surface, border, accent, positive, negative, warning. Never a raw colour value in a component; never a token outside its role.
- **One meaning per hue.** The accent means interactive; one filled accent action per view.
- **WCAG 2.2 AA.** Text 4.5:1; large text (≥ 24 sp regular, ≥ 18.7 sp bold) 3:1; icons and control boundaries that carry meaning 3:1. Measure the rendered pair against the surface it sits on, in light and dark.
- **Colour is never the only signal.** Pair it with a sign (+/−), an icon or a label.
- **Dark theme is its own palette.** Recheck every pair; inverted light values fail.

## Touch targets and accessibility

- **Minimum target 48 × 48 dp on Android**, 44 × 44 pt on iOS, 44 × 44 CSS px on touch web (WCAG floor 24 × 24). The visible shape may be smaller; the hit area is not.
- **Every icon-only control has a description naming the action** ("Close", not "X icon").
- **Smallest supported width**: 360 dp on Android, 320 CSS px reflow on web. **Large font**: render at 1.3 every round and at 2.0 on text-heavy screens; nothing clips, overlaps or wraps against the rules above.
- Respect the system reduce-motion setting (see `motion` and [compose.md](compose.md#reduced-motion)).

## UI writing

- **Sentence case** for titles, buttons, labels and tabs. "Save Changes" beside "Discard changes" reads as carelessness.
- **Buttons start with the verb** naming the action: "Log in", "Buy NVIDIA", "Transfer $500". A confirmation repeats the consequence.
- **The product's vocabulary only.** No implementation terms (sync, request, token, null, API, payload) on a screen.
- **No hedging and no status caveats.** Nothing that qualifies the product's own reality (beta, preview, demo, "for now") and no softeners on exact statements.
- **Errors say what happened and how to fix it, next to where it happened.** No blame, no exclamation marks.
- **Empty states** say what appears here, how to fill it, and offer one action.
- **One term per thing across a flow**; strings are full templates with plural forms, never fragments joined around a variable.

## Icons

- **One icon set and one stroke weight per surface.** Stroke follows adjacent text: 1.5 dp beside 400 weight, 2 dp beside 600 (24 dp grid).
- **Outline by default, filled for the selected state**; one vector tinted per state, never separate assets.
- **Native grid sizes** (16, 20, 24 dp); test at the smallest size the icon renders.
- **In RTL, mirror directional icons only** (back, forward, send); never logos, checkmarks or media controls.
- **Brand marks come only from the project's brand files**, never redrawn, set in a font or approximated.

## Press feedback

- **Respond on press-down within one frame.** Scale to 0.96 over 100–150 ms ease-out (project token wins), or a pressed fill step. Below 0.95 reads as a jump.
- **Interruptible.** Release animates back from the current scale, not from the pressed target.
- **Disabled controls do not scale.** Remove the platform ripple only when another press state replaces it.

## When not to animate

- **Actions repeated many times a day** (tab switches, keyboard shortcuts, typing, list navigation): no animation, or a colour change of 150 ms at most.
- **Data being read** (balances, prices, charts updating from a feed): no decorative motion and nothing that moves or resizes the value. A value may cross-fade in 200 ms or less, or mark a change with a tint that appears at once and fades out (up or down colour on the digits plus a soft background of the same hue, fading over up to 1000 ms ease-out); the value is readable for the whole fade, and nothing flashes on first render.
- **Every animation names its purpose**: feedback, spatial continuity, a state change, or preventing a jump. "Looks nice" on a frequent surface is not a purpose.
- **UI motion stays under 300 ms** (a fading change highlight that blocks nothing is the exception above), never uses ease-in, never scales from 0 (start ≥ 0.9 with opacity 0), and animates transform and opacity only.
- **Theme switches are instant**; cross-fading every colour at once makes a switch take visibly longer than the tap.
- **No enter animation on first render** for elements that are already in their default state.
- **Motion is never the only channel**: the end state shows the change without the animation.

## Enter and exit

`motion` owns stagger, durations, interruptibility and velocity handoff; read it for any transition.
Short form: exits are shorter than enters (150 ms against 250 ms); exit by a small fixed offset
(12 dp), not the full height; enter and leave along the same path; popovers scale from their
trigger, modals from the centre.

## Read the render as a person

Open every render and look before reading code. Walk these in order:

1. **Anchoring**: each element against the edge it belongs to; measure the distance.
2. **What moved that should not have**: compare old and new at the same size; any unrequested movement is a finding.
3. **Line breaks and wraps**: every text on its intended number of lines; no label, button, footer or identifier wrapped; no break inside a phrase, a value and unit, or brackets.
4. **Orphaned words** on the last line of headings and descriptions.
5. **Type roles**: every text uses a scale role; one display number; secondary text visibly secondary.
6. **Label wording**: read every string aloud against the writing rules and the profile's vocabulary.
7. **Rhythm**: gaps on the spacing scale; within-group gaps smaller than between-group gaps.
8. **Light and dark**: both themes, every pair readable, nothing disappearing.
9. **Smallest supported width** and **large font scale**: nothing clipped, overlapped or wrapped.

A collision check alone is not a review: a screen with no overlaps can fail every item above (example 2).

## Review output

| Severity | Location | What a person sees | Rule | Before → after |
| --- | --- | --- | --- | --- |
| Block | Login, `login-360-light.png`, `LoginScreen.kt:190` | The footer wraps after "Secured" | Wrapping is a decision | 3 lines → 2 rows, `maxLines = 1` each |

- **Block**: breaks reading or use, misses a numeric target beyond its tolerance, or hits a hard block in [review-checklist.md](review-checklist.md#hard-blocks). **Fix**: a visible inconsistency to correct this round. **Polish**: isolated refinement.
- Location names the screen, the render file and `path:line`. Before → after is numeric wherever a number exists.
- End with one line, `Verdict: Block` or `Verdict: Approve`. Approve only what you inspected; list uninspected renders as "Not inspected".

## Worked examples (ours)

1. An ask to "move the logo down and the button up" was implemented as a 16 dp shift nobody could see.
   The fix was numeric targets (logo centre at 28% of screen height, button bottom at 80%) and an
   old-versus-new render pair. Lesson: words like "down" and "up" are not targets; fractions are.
2. A trust footer was moved up from the bottom edge, wrapped onto a second line mid-phrase, and a build
   label sat outside its brackets. A collision-only review passed it. The fix was a bottom-anchored
   footer with two explicit rows (statement row, then a lighter monospace version row) that can never
   wrap. Lesson: read the render for breaks and anchoring, not only for overlaps.

---

Related: `motion` (transitions between states), `perceived-performance` (responsiveness and loading
states), `native-ui-craft` (iOS mechanics). Planning and review agents: `design-planner`, `design-reviewer`.
