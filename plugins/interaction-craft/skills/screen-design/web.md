# Web recipes

CSS and React equivalents of the rules in [SKILL.md](SKILL.md). Write every fix in the project's
styling system (custom properties, Tailwind classes, CSS modules) with its existing tokens.

## Proportional placement and anchoring

```css
/* First screen: logo centre at 28 % of the small viewport height, button bottom at 80 %. */
.first-screen { position: relative; min-height: 100svh; }
.first-screen .logo   { position: absolute; inset-inline: 0; margin-inline: auto; width: 128px;
                        top: calc(28svh - 64px); }
.first-screen .action { position: absolute; inset-inline: 20px; top: calc(80svh - 54px); height: 54px; }
.first-screen .footer { position: absolute; inset-inline: 20px;
                        bottom: calc(16px + env(safe-area-inset-bottom, 0px)); }
```

- `svh` for first screens and heroes (stable, never under the URL bar); `dvh` for app shells that track the visible area; plain `vh` overflows on mobile when the URL bar is shown.
- `env(safe-area-inset-*)` is 0 unless the viewport meta tag includes `viewport-fit=cover`.
- Ratios of gaps: `grid-template-rows: 28fr auto 72fr` distributes free space, like Compose weights.
- Use logical properties (`inset-inline`, `margin-inline-start`, `text-align: start`) so the layout mirrors in RTL.

## Spacing and grouping

```css
.field-group { display: flex; flex-direction: column; gap: 8px; }   /* within a group */
.form        { display: flex; flex-direction: column; gap: 24px; }  /* between groups */
```

Breakpoints come from where the content stops fitting, not device presets; prefer container
queries (`container-type: inline-size; @container (max-width: 400px) { … }`) for components.

## Text

```css
.label, .button, .tag, .footer-row { white-space: nowrap; }
h1, h2, h3 { text-wrap: balance; }
.description { text-wrap: pretty; }           /* no single word on the last line */
.identifier { overflow-wrap: anywhere; }       /* long IDs and URLs break instead of overflowing */
.amount, .price, .counter { font-variant-numeric: tabular-nums; }
.version, .build, .code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.prose { max-width: 65ch; }
.truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
```

- `&nbsp;` holds a value and unit together (`16&nbsp;GB`); `<bdi>` isolates a mixed-direction value.
- Prefer properties to raw feature tags: `font-variant-numeric: tabular-nums`, not `font-feature-settings: "tnum"`.
- Inputs use 16px text on mobile; smaller text makes iOS Safari zoom the page. Never disable zoom (`maximum-scale=1`, `user-scalable=no`).
- Store copy in natural case; apply case with `text-transform`.

## Press feedback

```css
.button {
  transition-property: scale, background-color;
  transition-duration: 150ms;
  transition-timing-function: cubic-bezier(0.23, 1, 0.32, 1);
  touch-action: manipulation;                  /* no double-tap zoom delay */
}
.button:active:not(:disabled) { scale: 0.96; }
html { -webkit-tap-highlight-color: transparent; }   /* only with an :active state on every control */

@media (hover: hover) and (pointer: fine) {
  .button:hover { background-color: var(--color-bg-hover); }   /* touch latches :hover after a tap */
}
```

Motion (React): `<motion.button whileTap={{ scale: 0.96 }} />`. Tailwind:
`transition-[scale,background-color] duration-150 ease-out active:scale-[0.96]`.

## Hit areas

```css
.icon-button { position: relative; width: 24px; height: 24px; }
.icon-button::after {
  content: ""; position: absolute; top: 50%; left: 50%;
  width: 44px; height: 44px; transform: translate(-50%, -50%);
}
.decorative-layer { pointer-events: none; }    /* a glow or scrim must not swallow taps */
```

Shrink an expanded hit area until it no longer overlaps a neighbouring one.

## Surfaces

```css
:root {
  --shadow-border:
    0 0 0 1px oklch(0 0 0 / 0.06),
    0 1px 2px -1px oklch(0 0 0 / 0.06),
    0 2px 4px 0 oklch(0 0 0 / 0.04);
}
.dark { --shadow-border: 0 0 0 1px oklch(1 0 0 / 0.08); }
.card { box-shadow: var(--shadow-border); }
.list-item + .list-item { border-top: 1px solid var(--color-border); }   /* structure stays a border */
img { outline: 1px solid oklch(0 0 0 / 0.1); outline-offset: -1px; }
.dark img { outline-color: oklch(1 0 0 / 0.1); }
```

## Motion hygiene

- Name the properties that transition; never `transition: all` or Tailwind `transition-all`.
- Animate `transform`, `opacity` and `filter`; `width`, `height`, `top`, `left`, `margin` and `padding` force layout every frame.
- `will-change: transform` only after a first-frame stutter is seen; never `will-change: all`.
- Wrap motion in `@media (prefers-reduced-motion: no-preference)` so it is opt-in; under reduce, replace movement with an opacity change.
- Suppress transitions during a theme switch: insert `*,*::before,*::after{transition:none!important}`, change the theme, read `document.body.offsetHeight` to flush styles, remove the rule after two animation frames (`next-themes` exposes this as `disableTransitionOnChange`).
- `AnimatePresence initial={false}` keeps elements present on first render from animating in.

## Numeric targets as tests

```ts
// Playwright: the logo centre sits at 28 % of the viewport height, ±1 %.
const vh = page.viewportSize()!.height;
const box = (await page.getByTestId("logo").boundingBox())!;
expect(Math.abs((box.y + box.height / 2) / vh - 0.28)).toBeLessThanOrEqual(0.01);
```

Render at 320 px wide and at 200% zoom; nothing scrolls horizontally (`document.documentElement.scrollWidth <= innerWidth`).
