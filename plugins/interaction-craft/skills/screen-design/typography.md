# Typography

The detail behind the typography rules in [SKILL.md](SKILL.md). Platform code is in
[compose.md](compose.md) and [web.md](web.md).

## A role scale, not a list of sizes

A role fixes size, weight, line height and tracking together, so choosing a role is one decision.
Name roles by use (`balance`, `rowTitle`, `caption`), not by size (`text-sm`). Where a project has no
scale, start here (sp on Android, px on the web):

| Role | Size | Weight | Line height | Tracking |
| --- | --- | --- | --- | --- |
| Display (one per screen: the number the screen answers) | 36–48 | 600 | 1.05–1.1 | −0.02 em |
| Title | 24–30 | 600 | 1.15–1.2 | −0.01 em |
| Heading | 18 | 600 | 1.3 | 0 |
| Body | 15–16 | 400 | 1.5 | 0 |
| Label, row title | 15 | 600 | 1.3 | 0 |
| Caption | 13 | 400 | 1.35–1.4 | 0 |
| Tag, uppercase eyebrow | 11–12 | 600 | 1.0–1.2 | +0.01 to +0.08 em |

- Emphasis inside a role is one weight step up (400 → 500 or 600), never a new size.
- Heading levels descend; adjacent deep levels may share a size if weight or spacing separates them. A child heading larger than its parent breaks the hierarchy.
- Three families at most; weight and size carry hierarchy. Pair families for contrast (serif titles over sans body), never two near-identical sans faces.
- Tracking depends on size: tighten large display text (−0.02 em), leave body at 0, open small uppercase labels (+0.05 em).
- Weight floor: 400 or heavier below 18 sp; weights under 300 only at 28 sp or larger.

## Line length

- Paragraphs: 45–75 characters per line. On a phone with 20 dp gutters at 15 sp the gutter already caps lines near 50 characters; on tablets and the web set a maximum width (`65ch`, about 560–680 px at 16 px).
- Never justify interface text; uneven word gaps slow reading.

## Line breaks: decide them

| Element | Lines allowed | Mechanism |
| --- | --- | --- |
| Button label, chip, tag, tab label | 1 | One line; shrink to 70% of the role size at most; then a shorter label |
| Footer, status line, version, identifier | 1 per row | Explicit rows, each one line; never a wrapped sentence |
| Row title | 1, or 2 with a clear reason | Ellipsis plus a path to the full value |
| Heading | 1–3 | Balanced breaks (`text-wrap: balance`, `LineBreak.Heading`) |
| Description | any | No orphan on the last line (`text-wrap: pretty`, `LineBreak.Paragraph`) |
| Money, quantities | 1 | Never wrapped or truncated; the layout makes room |

Checks for every text element:

- The break never falls inside a value and its unit, inside brackets, inside a version string, or between a name's parts.
- A one-line element stays one line at the smallest supported width (360 dp, 320 px) and at font scale 1.3.
- Two pieces of information that do not fit one line become two rows, each with its own role; the secondary row is lighter (secondary colour) or smaller.
- The last line of a heading or description is not a single short word.

## Numbers

- Tabular lining figures for any value that changes (balances, prices, timers, counters) or sits in a column; the row width then stays fixed as digits change.
- Right-align numbers in columns (trailing edge), left-align text (leading edge).
- Negative values use the minus sign U+2212, not a hyphen; ranges use an en dash (2010–2020); the ellipsis is one character (…).
- Currency formatting follows the locale and keeps a consistent number of decimals within one list.
- Digit order never reverses in RTL; isolate mixed-direction values.

## Versions, identifiers and codes

- Set in monospace: version strings, build numbers, order and transaction IDs the person reads out, one-time codes, hashes shown on purpose.
- Monospace rows are secondary: one step lighter in colour, and the same size or smaller than the statement beside them.
- Keep the whole string on one line: `v1.2.3 (build 45)`, with no break inside the brackets.
- Group long codes for reading (`4F2A 9C1B`), and let them be selected and copied.

## Truncation

- One line: ellipsis at the end. Several lines: clamp with an ellipsis.
- Truncated content is reachable: a detail view, an expanded state or a long-press.
- Never truncate money, a quantity, or a name the person must verify before confirming.

## Size floors and scaling

- Minimum 12 sp for any text; captions 13 sp; body 15–17 sp on phones; web body starts at 16 px.
- Web inputs are 16 px on mobile; smaller text triggers page zoom on iOS Safari.
- Text scales with the system font setting: sizes in sp (Android), Dynamic Type (iOS), rem (web). Fixed heights on text containers clip at large scale; use minimum heights.

## Wording that renders

- Sentence case for every interface string; write copy in natural case and apply transforms in style code.
- Curly quotes in prose, straight quotes in code.
- One term per concept across the product; the term in the menu is the term in the confirmation.
