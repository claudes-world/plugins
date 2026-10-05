# Surfaces and colour

The detail behind the surface and colour rules in [SKILL.md](SKILL.md).

## Concentric radii

`outer radius = inner radius + padding`

| Inner radius | Padding | Outer radius |
| --- | --- | --- |
| 8 | 8 | 16 |
| 12 | 8 | 20 |
| 16 | 4 | 20 |
| pill (999) | any | pill (999) |

- Applies when the inner shape sits at an even inset close to the outer edge. Past 24 dp of padding the shapes read as separate surfaces; choose each radius independently.
- When the project's radius tokens do not contain the computed value, keep the outer token and reduce the inner one, or propose a token by name; never introduce an unnamed radius.
- A pill inside a pill stays a pill: a fully rounded end is concentric at any padding.

## Shadow or border

| Use a shadow (elevation) | Use a border (structure) |
| --- | --- |
| Sheets, dialogs, menus, popovers | Dividers between rows |
| Toasts and floating buttons | Cards in a flat design system |
| An element being dragged | Text fields (also needed for the field's own boundary) |
| A raised segment thumb or toggle thumb | Selected and focus states |

- A flat system separates cards with a 1 dp border in the line colour and reserves shadow for the few surfaces that sit above the page. Mixing shadowed and bordered cards on one screen reads as two systems.
- Shadows use transparency and adapt to any background; a solid border colour is chosen for one background.
- Dark theme: shadows are not visible; separate with a surface one step lighter than the page, or a 1 dp ring at 8% white (13% on hover).
- Separators stay quiet: 1 dp, low contrast, and never combined with a large gap that already separates the groups.
- One surface, one job: the page background is for content set directly on it; a raised (white or lighter) surface marks something the person can act on or own. A box around every group removes hierarchy.

## Images and translucency

- Images: 1 dp outline inside the edge, 10% black on light and 10% white on dark. Never a tinted neutral or the accent colour.
- Scrims behind sheets: the ink colour at 30–40% on light, near-black at 50–60% on dark; the scrim fades in over the same duration as the sheet.
- Text on a translucent or blurred surface is measured against the lightest and darkest content that can scroll beneath it; if either fails, raise the surface opacity.
- Never stack a light translucent surface on another translucent surface; text contrast collapses.

## Colour system

- Two tiers. Primitives name a value (`green-700`) and are never used in a component. Semantic tokens name a role (`text-secondary`, `surface`, `line`, `accent`, `positive`, `negative`, `warning`) and are the only tier components read.
- Use a token only in its role. A border token used as a text colour changes when borders change.
- If a role has no token, propose one by name and role; never borrow another role's token because its value matches today.
- One hue, one meaning across the product; hues within 15° read as the same colour. If the accent means interactive, static text never uses it.
- One filled accent action per view; secondary actions are outlined or plain.
- Status colours (positive, negative, warning) appear only on the thing whose status they describe, and always with a second cue: a sign, an icon or a word.
- Gain and loss colours depend on locale: green up and red down in Western markets, red up and green down in Chinese markets. A product shipping to both makes them locale tokens.

## Contrast

| Content | WCAG 2.2 AA | AAA |
| --- | --- | --- |
| Text below 24 sp (18.7 sp bold) | 4.5:1 | 7:1 |
| Text at or above 24 sp (18.7 sp bold) | 3:1 | 4.5:1 |
| Icons, control boundaries, focus indicators that identify a control | 3:1 | |
| Disabled controls | exempt (still legible enough to identify) | |

- Measure the rendered foreground against the surface it actually sits on, not the page background.
- Measure both themes; a pair that passes in light can fail in dark.
- On a failing pair, change lightness, not hue; hue shifts move contrast little. Recheck after every change.
- Report a failing pair with its measured ratio and the threshold; a colour change is a design decision named as a proposal.

Relative luminance and ratio (sRGB hex in, ratio out):

```python
def luminance(hex_colour):
    r, g, b = (int(hex_colour.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    lin = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)

def contrast(fg, bg):
    hi, lo = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)

contrast("#7D8C81", "#F7F8F4")   # 3.31: fails 4.5:1 for small text
```

From a render, read the text's darkest pixel and the background beside it with PIL
(`Image.getpixel`) and pass both through the same function; antialiasing lightens edge pixels, so
take the darkest pixel inside a glyph stem.

## Dark theme

- A separate palette, not an inversion: lower the vividness of accents, widen the steps at the dark end, then recheck every text pair.
- Surfaces get lighter as they rise (page darkest, raised surfaces lighter).
- Pure black pages (#000) cause smearing on OLED during scroll; use a near-black page token.
- Brand marks drawn in dark ink are tinted to the light ink colour on dark pages, from the same artwork.
