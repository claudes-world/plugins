
# Codex image_gen — generated images plus local procedural post-processing

## When to use

- **Illustrations, photographs, blog heroes, posters, thumbnails, and textures**
- **Game terrain / strategy maps** with known layout coordinates (matches a code spec)
- **UI mockups, sprites, icons** that read at small sizes and benefit from pixel-art aesthetic
- **Deterministic renders** you may want to re-tweak parametrically later
- Any case where the output needs to be on-brand, from stylised to photoreal

## When NOT to use

- Vector output requirements (SVG) — codex can do that too but use a different prompt pattern
- Animated content

## Built-in generation

Use a Codex installation with access to the built-in `image_gen` tool for
illustrative or photographic work. Availability depends on the host and account;
report unavailable capability rather than substituting another provider.

**How to invoke it from a Claude lane:** launch `codex exec` detached so the
lane remains responsive, but poll that exact PID in the foreground with a hard
deadline. The prompt must name the built-in `image_gen` tool, give an absolute
output path, ban substitution, and request a clear final status. For example:

```bash
OUT=/absolute/path/to/output.png
PROMPT_FILE=/tmp/codex-image-gen-prompt.txt
LOG=/tmp/codex-image-gen.log
printf '%s\n' \
  "Use the built-in image_gen tool to create a real model-rendered 1600x900 PNG: <SUBJECT, STYLE, MOOD, PALETTE, COMPOSITION>. Save it to $OUT. Do not use any Google image service or another paid provider. If image_gen is unavailable, STOP; do not fall back to another generator or PIL. End with RESULT: GENERATED $OUT via image_gen, or RESULT: CANNOT — <reason>." \
  >"$PROMPT_FILE"
nohup codex exec --skip-git-repo-check --sandbox workspace-write \
  --add-dir "$(dirname "$OUT")" -c sandbox_workspace_write.network_access=true \
  -c approval_policy=never - \
  <"$PROMPT_FILE" >"$LOG" 2>&1 &
IMAGE_JOB_PID=$!

DEADLINE=$((SECONDS + 360))
while kill -0 "$IMAGE_JOB_PID" 2>/dev/null; do
  if (( SECONDS >= DEADLINE )); then
    kill "$IMAGE_JOB_PID" 2>/dev/null || true
    wait "$IMAGE_JOB_PID" 2>/dev/null || true
    echo "image_gen timed out; inspect $LOG" >&2
    exit 124
  fi
  sleep 5
done
wait "$IMAGE_JOB_PID"
test -s "$OUT"
```

Do not hand the polling loop to another detached helper: the active lane owns
the bounded wait, exit status, output-file check, and visual inspection. A
one-shot alternative is `${CLAUDE_PLUGIN_ROOT}/bin/gen-image "<prompt>" -o
/absolute/path/out.png --aspect 16:9`; that wrapper executes the same Codex-only
route with a timeout. Note `-i/--image` remains attach-only (not generation).

**Targeted EDIT / recolor of an existing image**: attach the source image with `-i <FILE>` (and optionally a second `-i` color-reference image), and codex's image_gen model can recolor/edit it while preserving shape, edges, and a transparent background — genuinely well. TWO gotchas: (1) **the variadic `-i` flag greedily eats a trailing positional prompt** — `-i A -i B "prompt"` makes codex treat "prompt" as a third image → empty prompt → hangs on stdin. Pass the prompt via **stdin pipe** (`cat prompt.md | codex exec … -i A -i B`) with NO trailing positional. (2) **Codex will quietly FALL BACK to a deterministic/PIL recolor** if the task stresses exactness ("preserve transparency exactly") — it judges a script safer. If you specifically want the generative model's output, say so explicitly: *"You MUST use the generative image_gen model, NOT a script/deterministic recolor."* Otherwise you'll get a (fine, but non-generative) scripted result. Steering lesson: name the tool you want or codex picks for you.

**DO NOT run codex image_gen jobs in PARALLEL**: Run image-gen jobs **sequentially** (a `for` loop, one after another). "Parallel image gen" = sequential codex calls, not concurrent processes. (Costs wall-clock, but each ~1–2 min and correctness > speed.)

**When PIL is STILL the right tool (the original pattern, below):** local post-processing (pixelise, palette-quantise, resize, composite), deterministic/parametric renders you'll re-tweak in code, assets that must align to exact pixel coordinates from a code spec (game terrain/strategy maps, sprite atlases, UI mockups), or anything where reproducibility matters more than painterly fidelity. For those, codex writes a Python+PIL/Pillow procedural renderer — still surprisingly good for terrain, abstract maps, pixel-art sprites, parchment textures, branded cards with exact-placed text. PIL is not a fallback for a requested generative image: if built-in `image_gen` is unavailable, stop.

Rule of thumb: **illustrative/editorial/painterly → built-in image_gen; deterministic/coordinate-exact/parametric → PIL.**

## The pattern

```bash
codex exec "Create a deterministic <ASSET_TYPE> PNG with Python+PIL/Pillow and save it to <ABSOLUTE_PATH>. <SIZE> px. <REGION/COMPONENT_LAYOUT_AT_COORDINATES>. <PALETTE_HINTS>. <NEGATIVE_CONSTRAINTS like 'NO text labels, NO grid lines'>. This is explicitly a procedural-rendering or local post-processing task, not generative image creation." \
  --skip-git-repo-check \
  --sandbox workspace-write
```

### Required flags

- `--sandbox workspace-write` — codex needs to write Python scripts and the output PNG. Read-only sandbox blocks file writes.
- `--skip-git-repo-check` — outside-repo invocations from `/tmp` or `~/` need this; harmless to pass always.

### Prompt pattern that works

1. **Specify absolute output path** ("save to /tmp/foo.png") — codex won't pick a sensible default and will sometimes write to its scratch dir.
2. **Specify exact dimensions** in pixels, not aspect ratio. Aspect ratios like "16:9" get loosely interpreted. State "800x600 PNG" if that's what you mean.
3. **Give coordinate layout** if the asset must align with code (e.g. a Pixi canvas REGIONS array). Codex's renders are noticeably tighter when prompted with "forest at x=150,y=100 in an 800x600 canvas" vs "forest in the top-left."
4. **Negative constraints** — "NO text labels," "NO grid lines," "NO color names rendered." These get violated otherwise.
5. **No generator fallback** — use the procedural prompt only when the requested result is genuinely deterministic/local post-processing. Never use PIL to disguise a failed generative request.

## Limitations / gotchas (PIL path)

- **No real image gen** — output is procedural Python art, not diffusion. Realism ceiling is "stylized pixel-art" or "tasteful abstract."
- **Codex sometimes overwrites your fallback file** at the same path — if you're racing codex against a procedural fallback, use different paths and pick the better one after.
- **Wall-clock time is 2-3 minutes** for a moderately detailed render. Long for chat sessions. Run in background and have a procedural fallback queued.
- **Output is RGBA** by default. Convert to RGB if your downstream tool can't handle alpha (e.g. some Pixi importers).
- **No text rendering** — codex sometimes adds tiny pixel-font labels even when told not to. Prompt firmly + visually inspect.
- **Coordinates can drift slightly** from spec — codex's blob renderers center things ~10-30px off the requested coords. Acceptable for backgrounds where interactive markers overlay; not acceptable for sprite atlases.
- **Codex's session-recording errors** are noisy at end (`failed to record rollout items: thread ... not found`) but don't affect output. Ignore.
