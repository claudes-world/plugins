# Compose recipes

Jetpack Compose translations of every rule in [SKILL.md](SKILL.md), with SwiftUI equivalents at the
end. Read colours, type, spacing, radii and durations from the project's theme objects; the literal
numbers below stand in only where the project has no token.

## Proportional placement

Place hero content by a fraction of the height, measured inside `BoxWithConstraints`.

```kotlin
BoxWithConstraints(Modifier.fillMaxSize()) {
    val h = maxHeight                       // window height; subtract insets for safe height
    val logo = 128.dp
    // Logo centre at 28 % of the height: place its top at 0.28 h − half its size.
    Box(Modifier.align(Alignment.TopCenter).offset(y = h * 0.28f - logo / 2).size(logo))
    // Button bottom edge at 80 %: place by the bottom edge, not the top.
    PrimaryButton(
        Modifier.align(Alignment.TopCenter).offset(y = h * 0.80f - 54.dp)
            .fillMaxWidth().padding(horizontal = 20.dp).height(54.dp),
    )
}
```

`BiasAlignment` positions within the free space (container minus child), not the full height.
A child of size `s` aligned with vertical bias `b` has its top at `(H − s) × (1 + b) / 2`. For a
centre at fraction `f` of `H`, the bias is `b = 2 × (f × H − s / 2) / (H − s) − 1`, which depends
on `H`: compute it inside `BoxWithConstraints`, or state the target as a fraction of free space.
Example: `H` 915 dp, `s` 128 dp, `f` 0.28 gives `b` = −0.512.

`Modifier.weight` in a `Column` splits the space left after fixed-size children. Two spacers with
`weight(28f)` and `weight(72f)` put 28% of the free space above the content, not the content at 28%
of the screen. Use weights when the target is a ratio of gaps; use the offset arithmetic when the
target is a position.

On short screens, protect the space between anchored elements: compute the band between them and
move the upper element up (never past the status bar plus 8 dp) when the band falls below its minimum.

## Bottom-anchored elements and insets

```kotlin
// Call enableEdgeToEdge() in the activity; then every edge element pads for its own inset.
Column(
    Modifier.align(Alignment.BottomCenter).fillMaxWidth()
        .navigationBarsPadding()                 // or windowInsetsPadding(WindowInsets.safeDrawing)
        .padding(start = 20.dp, end = 20.dp, bottom = 16.dp),
    horizontalAlignment = Alignment.CenterHorizontally,
) { /* footer rows */ }
```

- Measure bottom targets from the navigation bar inset, top targets from the status bar inset.
- The gesture navigation inset is 24 dp on most devices and three-button navigation 48 dp; render both when a bottom element matters.
- A screen with a text field adds `Modifier.imePadding()` to the element that must stay above the keyboard.
- Keep scrolling content clear of a fixed footer: give the content a bottom spacer equal to the footer's measured height plus the gap.

## Text that never wraps: explicit rows

```kotlin
// Two explicit rows: the statement, then the version in monospace, lighter.
Text(statement, style = type.caption, color = colors.textSecondary,
    maxLines = 1, softWrap = false, textAlign = TextAlign.Center)
Text(version, style = type.caption.copy(fontFamily = FontFamily.Monospace), color = colors.textTertiary,
    maxLines = 1, softWrap = false, textAlign = TextAlign.Center)
```

- `softWrap = false` with `maxLines = 1` guarantees one line; it does not guarantee the line fits. Check fit with the measurer at the current font scale and choose the layout from the result:

```kotlin
val measurer = rememberTextMeasurer()
val fits = !measurer.measure(label, style, maxLines = 1, softWrap = false,
    constraints = Constraints(maxWidth = widthPx)).didOverflowWidth
if (fits) Row { /* one line */ } else Column { /* two explicit rows */ }
```

- Reserve the height of anchored text from the same measurement (sum of row heights), so content above stays a fixed distance clear at every font scale.
- Button labels that must stay on one line can shrink within limits. `TextAutoSize` is experimental (`@ExperimentalFoundationApi` or the current opt-in) and its API may change: `BasicText(label, maxLines = 1, autoSize = TextAutoSize.StepBased(minFontSize = size * 0.7, maxFontSize = size, stepSize = 0.5.sp))`.
- Hold units together with a no-break space: `"16 GB"`, `"v1.2.3 (build 45)"`. A word joiner `⁠` stops a break without adding space.
- Headings: `TextStyle(lineBreak = LineBreak.Heading)` balances line lengths. Descriptions: `LineBreak.Paragraph` with `hyphens = Hyphens.Auto` reduces ragged and orphaned last lines.

## Numbers and identifiers

```kotlin
val amount = type.value.copy(fontFeatureSettings = "tnum, lnum")   // tabular lining figures
val build = type.caption.copy(fontFamily = FontFamily.Monospace)   // versions, IDs, codes
```

Use the real minus sign `"−"` for negative values; a hyphen is narrower and misaligns columns.

## Press feedback

```kotlin
@Composable
fun Modifier.pressScale(onClick: () -> Unit, enabled: Boolean = true, pressed: Float = 0.96f): Modifier {
    val source = remember { MutableInteractionSource() }
    val isPressed by source.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (isPressed && enabled) pressed else 1f,
        animationSpec = tween(durationMillis = 120, easing = EaseOutStrong),
        label = "press",
    )
    return this
        .graphicsLayer { scaleX = scale; scaleY = scale }   // read in the draw phase: no recomposition per frame
        .clickable(source, indication = ripple(), enabled = enabled, role = Role.Button, onClick = onClick)
}
```

- `animateFloatAsState` retargets from the current value, so a release mid-press returns smoothly.
- Pass `indication = null` only when a pressed fill colour replaces the ripple.
- Use the project's press scale and duration tokens when they exist.

## Concentric radii

```kotlin
val inner = 12.dp
val padding = 8.dp
val outer = inner + padding                       // 20.dp
Box(Modifier.clip(RoundedCornerShape(outer)).background(colors.surface).padding(padding)) {
    Box(Modifier.clip(RoundedCornerShape(inner)).background(colors.surfaceRaised))
}
```

## Surfaces

- Structure: `Modifier.border(1.dp, colors.line, shape)`. Compose draws the border inside the bounds, so it adds no size.
- Elevation: `Modifier.shadow(8.dp, shape)` or `Surface(shadowElevation = 8.dp)`. Set `tonalElevation = 0.dp` when the project defines its own surface colours; Material 3 tonal elevation tints the surface.
- Image outline: `Modifier.border(1.dp, Color.Black.copy(alpha = 0.1f), shape)` in light, `Color.White.copy(alpha = 0.1f)` in dark.

## Touch targets and semantics

```kotlin
Box(
    Modifier.minimumInteractiveComponentSize()        // 48 dp hit area around a smaller visual
        .clickable(onClickLabel = "Close", role = Role.Button, onClick = onClose),
    contentAlignment = Alignment.Center,
) { Icon(Icons.Default.Close, contentDescription = "Close", modifier = Modifier.size(24.dp)) }
```

- Material components already apply the 48 dp minimum; custom `clickable` elements do not.
- Merge a row into one announcement with `Modifier.semantics(mergeDescendants = true) {}`.
- Directional icons: use auto-mirrored vectors (`Icons.AutoMirrored.*`, `android:autoMirrored="true"` in vector XML).

## Animation specs

```kotlin
val EaseOutStrong = CubicBezierEasing(0.23f, 1f, 0.32f, 1f)       // enters, press feedback
val EaseInOutStrong = CubicBezierEasing(0.77f, 0f, 0.175f, 1f)    // movement between two resting places
val EaseStandard = CubicBezierEasing(0.2f, 0f, 0f, 1f)            // Material standard
```

| Change | Spec |
| --- | --- |
| Press scale (UI motion is at most 300 ms) | `tween(100–150, easing = EaseOutStrong)` |
| Colour of a control state | `tween(150, easing = LinearEasing)` |
| Small element enters | `fadeIn(tween(250, easing = EaseOutStrong)) + slideInVertically(tween(250, easing = EaseOutStrong)) { offset12dpPx }` |
| Small element exits | `fadeOut(tween(150)) + slideOutVertically(tween(150)) { -offset12dpPx }` |
| Sheet or screen transition | Duration from the ranges in `motion` (at most 300 ms), `EaseStandard` or the project's sheet token |
| On-screen movement between two resting places | `tween(200–300, easing = EaseInOutStrong)` |
| Fading change highlight that blocks nothing | `tween(up to 1000, easing = EaseOutStrong)` on the tint; the value stays readable |
| Gesture release | `spring(dampingRatio = Spring.DampingRatioNoBouncy, stiffness = Spring.StiffnessMediumLow)` with the gesture velocity (see `motion`) |

Theme colours apply instantly. A component that animates colour with `animateColorAsState` must
snap when the theme changes, or the switch cross-fades every surface at once:

```kotlin
var lastDark by remember { mutableStateOf(isDark) }
val spec: AnimationSpec<Color> = if (lastDark != isDark) snap() else tween(150)
SideEffect { lastDark = isDark }
val fill by animateColorAsState(target, spec, label = "fill")
```

## Reduced motion

Compose applies the system animator duration scale to `animate*AsState`, `Animatable` and
transitions; when "Remove animations" sets it to 0 they jump to their end state. Loops you drive
yourself (`withFrameNanos`, a custom clock) are not scaled: read the setting and replace movement
with a short opacity change.

```kotlin
@Composable
fun rememberReduceMotion(): Boolean {
    val resolver = LocalContext.current.contentResolver
    // Re-read on resume (or observe with a ContentObserver) if the screen stays open across a settings change.
    return remember(resolver) {
        Settings.Global.getFloat(resolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f) == 0f
    }
}
```

## Numeric targets as tests

Tag the elements a target names and assert their bounds; the target then holds on every build.

```kotlin
@Test fun logoCentreAt28Percent() {
    compose.setContent { AppTheme { LoginScreen(/* … */) } }
    val root = compose.onRoot().getUnclippedBoundsInRoot()          // DpRect
    val logo = compose.onNodeWithTag("login-logo").getUnclippedBoundsInRoot()
    val centre = (logo.top + logo.bottom) / 2
    assertEquals(0.28f, centre / root.height, 0.01f)          // Dp / Dp is a Float; tolerance: 1 % of the height
}
```

`getUnclippedBoundsInRoot()` comes from the `androidx.compose.ui:ui-test` artifact (`ui-test-junit4` brings it in transitively).

## Renders

- Roborazzi on Robolectric: `compose.onRoot().captureRoboImage("build/screens/<name>.png")`.
- Size and theme by qualifier: `@Config(qualifiers = "w360dp-h740dp-xhdpi")`, dark with `-night-`.
- Font scale: wrap content in `CompositionLocalProvider(LocalDensity provides Density(LocalDensity.current.density, fontScale = 1.3f))`.
- At `xhdpi` one dp is 2 px; convert measurements before comparing them with dp targets.

## SwiftUI equivalents

| Rule | SwiftUI |
| --- | --- |
| Proportional placement | `GeometryReader { g in … .position(x: g.size.width / 2, y: g.size.height * 0.28) }` |
| Bottom anchoring | `.safeAreaInset(edge: .bottom) { footer }` or `.padding(.bottom, 16)` inside the safe area |
| One line | `.lineLimit(1)`, `.fixedSize(horizontal: false, vertical: true)`; shrink with `.minimumScaleFactor(0.7)` |
| Tabular figures | `.monospacedDigit()` |
| Monospace identifier | `.font(.caption.monospaced())` |
| Press scale | `ButtonStyle` with `.scaleEffect(configuration.isPressed ? 0.96 : 1)` and `.animation(.easeOut(duration: 0.12), value: configuration.isPressed)` |
| Concentric corners | `RoundedRectangle(cornerRadius: inner + padding, style: .continuous)` |
| Touch target | `.frame(minWidth: 44, minHeight: 44).contentShape(Rectangle())` |
| Reduced motion | `@Environment(\.accessibilityReduceMotion) var reduceMotion` |
| Large text | `.dynamicTypeSize(...DynamicTypeSize.accessibility3)` to cap only where layout cannot reflow |
