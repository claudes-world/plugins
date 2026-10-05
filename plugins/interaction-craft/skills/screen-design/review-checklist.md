# Review checklist

The full list a design reviewer walks. Each item is checkable from a render (`[render]`), from code
(`[code]`), or both. Rules and numbers are in [SKILL.md](SKILL.md); measurement recipes are at the end.

## Hard blocks

Hard blocks apply to elements the change introduced, modified or moved. A hard-block condition on an untouched element is reported in a separate "Pre-existing" table and does not by itself make the verdict Block. Any hard block on such an element makes the verdict `Block`, whatever else the screen gets right:

1. Text that wraps or truncates where the design did not intend it (labels, buttons, footers, versions, identifiers, money).
2. An element that moved, resized or changed colour without being asked.
3. A numeric target missed by more than its tolerance (default 1% of the screen dimension, or 2 dp for fixed values).
4. Text contrast below WCAG AA (4.5:1, or 3:1 for text at 24 sp and above or 18.7 sp bold and above).
5. A touch target under 48 × 48 dp (44 × 44 pt on iOS, 44 × 44 px on touch web).
6. Hedging, status-caveat or jargon wording on a screen, or wording against the project profile's vocabulary.
7. A brand mark that does not come from the project's brand files.

## A. Targets and movement

- [render] Every numeric target in the plan, measured, with the measured value and the difference from target.
- [render] Old and new renders of the same state at the same size compared; every changed region accounted for by the plan.
- [render] The change is visible at normal viewing distance (at least 4% of the screen height for a move the requester asked to see).
- [code] Targets are expressed as fractions or tokens in code, not as a one-off offset tuned by eye.

## B. Anchoring and layout

- [render] Each element sits against the edge it belongs to: headers to the top inset, footers and docks to the bottom inset, hero content at its fraction.
- [render] Nothing sits under the status bar, cutout or navigation bar; nothing touches the screen edge except full-bleed backgrounds and media.
- [render] One filled primary action; the fact the person came for is top and leading.
- [render] Controls are visibly controls (fill, border or fixed control position).
- [code] Bottom-anchored elements pad for the navigation bar inset; content above reserves their measured height.
- [code] No fixed heights on containers holding text.

## C. Spacing, alignment and shape

- [render] Gaps fall on the spacing scale; gaps between groups at least twice the gaps within them.
- [render] Elements in a column share one leading edge; no 1–3 dp strays.
- [render] Icons in buttons and play glyphs are optically centred.
- [render] Nested rounded shapes are concentric (outer = inner + padding) where the inset is 24 dp or less.
- [code] Every spacing, radius and size value is a token; any new value is named as a proposal.

## D. Text: breaks and wraps

- [render] Every text element is on its intended number of lines at the default width.
- [render] No break inside a phrase, a value and its unit, brackets, or a version string.
- [render] No orphaned single word on the last line of a heading or description.
- [render] At the smallest supported width and at font scale 1.3 (and 2.0 for text-heavy screens): nothing wraps that must not, nothing clips, nothing overlaps.
- [code] One-line text is constrained to one line (`maxLines = 1`, `softWrap = false`, `white-space: nowrap`) and its fit is checked or guaranteed by layout.
- [code] Two pieces of information that cannot share a line are two explicit rows.

## E. Type roles

- [render] Every text uses a role from the scale; one display-size number per screen.
- [render] Secondary text is visibly secondary (colour or size), and heading levels descend.
- [render] Changing numbers use tabular figures; versions, build numbers and IDs are monospace and lighter than the statement beside them.
- [code] Text styles come from the type scale; no inline font sizes or weights.
- [code] Negative numbers use U+2212; ranges use an en dash.

## F. Colour and contrast

- [render] Every text pair measured in light and dark against its actual surface; ratios listed for anything near the threshold.
- [render] Status colours have a second cue (sign, icon or word).
- [render] Dark theme: nothing disappears; no shadow-only separation.
- [code] Colours come from role tokens; no raw values; no token used outside its role.

## G. Surfaces

- [render] Shadows only on surfaces above the page; borders for structure; never both for one purpose.
- [render] Images carry the 1 dp neutral outline where the project uses it.
- [code] No Material tonal elevation tint where the project defines its own surfaces.

## H. Icons and brand

- [render] One icon set and stroke weight per surface; stroke matches adjacent text weight.
- [render] Outline for default, filled for selected.
- [render] The brand mark matches the brand file exactly (shape, proportions, colour); in dark theme it is the same artwork tinted.
- [code] The brand mark is loaded from the asset converted from the brand file, not drawn in code or set in a font.

## I. Touch and accessibility

- [render] Every target at least 48 × 48 dp (hit area, not visible shape); adjacent hit areas do not overlap.
- [code] Every icon-only control has a description naming the action; rows merge into one announcement where they act as one.
- [code] Reduced motion handled: system-scaled animations need nothing extra; hand-driven loops check the setting.

## J. Wording

- [render] Read every string aloud: sentence case; buttons start with a verb; one term per concept.
- [render] No hedging, status-caveat or implementation words; vocabulary matches the project profile.
- [render] Errors say what happened and how to fix it, next to where it happened; empty states say what appears and offer one action.

## K. States

- [render] Light and dark rendered for every changed screen.
- [render] Smallest supported width and large font scale rendered.
- [render] Empty, loading, error, pending and disabled states rendered where the screen has them.

## L. Motion and press feedback

- [code] Every pressable element responds on press-down (scale 0.96 or the project token, 100–150 ms ease-out, or a pressed fill).
- [code] No animation on high-frequency actions or on data being read; UI motion at most 300 ms, sheet and screen transitions within the ranges in `motion`, a fading change highlight that blocks nothing up to 1000 ms; no pure ease-in, ease-in-out only for on-screen movement between two resting places; no scale from 0; only transform and opacity animated.
- [code] Theme switches do not cross-fade every colour.
- [code] Enter and exit follow `motion`: exits shorter than enters, same path in and out.

## Measuring a render

Renders from Robolectric at `xhdpi` are 2 px per dp. Choose each region from the image itself (open
it first), then measure the ink bounding box inside it:

```python
from PIL import Image, ImageChops

def bbox(path, region=(0.0, 0.0, 1.0, 1.0), tol=24, density=2.0):
    """Ink box inside region (x0, y0, x1, y1 as fractions). Background = most common colour there."""
    im = Image.open(path).convert("RGB")
    W, H = im.size
    x0, y0, x1, y1 = (int(region[0] * W), int(region[1] * H), int(region[2] * W), int(region[3] * H))
    crop = im.crop((x0, y0, x1, y1))
    bg = max(crop.getcolors(crop.width * crop.height), key=lambda c: c[0])[1]
    mask = ImageChops.difference(crop, Image.new("RGB", crop.size, bg)).convert("L").point(lambda v: 255 if v > tol else 0)
    box = mask.getbbox()
    if box is None:
        return None
    l, t, r, b = box[0] + x0, box[1] + y0, box[2] + x0, box[3] + y0
    return {"centre_y": (t + b) / 2 / H, "top_y": t / H, "bottom_y": b / H, "centre_x": (l + r) / 2 / W,
            "size_dp": ((r - l) / density, (b - t) / density), "bottom_gap_dp": (H - b) / density}

print(bbox("new/login.png", (0.3, 0.05, 0.7, 0.30)))   # logo region, chosen from the image
```

- The ink box of artwork with internal padding is smaller than its layout box; its centre still holds for centred artwork. For exact edges use the layout bounds from a test (see [compose.md](compose.md#numeric-targets-as-tests)).
- A region that catches a neighbouring element gives a wrong box: tighten it and measure again.

Find everything that changed between old and new:

```python
def changed(old, new, tol=24):
    a, b = Image.open(old).convert("RGB"), Image.open(new).convert("RGB")
    diff = ImageChops.difference(a, b).convert("L").point(lambda v: 255 if v > tol else 0)
    return diff.getbbox()        # None when identical; compare with the regions the plan names
```

Compose an old-versus-new pair for the contact sheet:

```python
from PIL import ImageDraw

def pair(old, new, out, gap=24, header=40):
    a, b = Image.open(old).convert("RGB"), Image.open(new).convert("RGB")
    sheet = Image.new("RGB", (a.width + gap + b.width, max(a.height, b.height) + header), "white")
    sheet.paste(a, (0, header))
    sheet.paste(b, (a.width + gap, header))
    draw = ImageDraw.Draw(sheet)
    draw.text((8, 12), f"old  {old}", fill="black")
    draw.text((a.width + gap + 8, 12), f"new  {new}", fill="black")
    sheet.save(out)
```
