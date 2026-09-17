# Local background removal

## Use it only as a fallback

Ask Codex `image_gen` for a genuinely transparent background first. Native
transparency preserves the generator's intended soft edges. Run `scripts/bg-remove` only when the
generator returned an opaque background, when removing a background from an
existing raster, or when validating/cleaning an existing cutout. Never call a
paid background-removal or image API.

Do not raster-process an SVG; edit the vector source. Avoid re-segmenting an
already-transparent image: the CLI detects real alpha and preserves it.

## CLI

From an installed plugin:

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/image-assets/scripts/bg-remove" input.png \
  -o output.png
```

The default path uses the free local `rembg` package with its `u2net` ONNX
model. The first run may download model weights; it does not call an inference
API. Install dependencies in an isolated environment:

```bash
python3 -m venv ~/.venvs/rembg
~/.venvs/rembg/bin/pip install pillow 'rembg[cpu]'
~/.venvs/rembg/bin/python \
  "${CLAUDE_PLUGIN_ROOT}/skills/image-assets/scripts/bg-remove" input.png \
  -o output.png
```

Useful controls:

- `--keep-shadow` asks rembg for a soft alpha matte. It can retain natural
  shadows, but inspect the result because the model still decides foreground.
- `--halo-clean` removes one light, neutral fringe pixel at the transparent
  boundary; `--halo-clean 2` removes two edge-band pixels. It does not erode
  dark outlines or interior alpha. Inspect on both light and dark backgrounds.
- Alpha verification is on by default and exits 3 unless the result has visible
  content plus meaningful transparency: at least 2% non-opaque pixels or at
  least 10% of border samples non-opaque. `--no-verify-alpha` is the explicit
  escape hatch for inspecting a deliberately raw result.
- `--model u2netp` trades quality for speed. The only allowed neural models are
  `u2net` and `u2netp`; both run locally and inherit the upstream U²-Net
  Apache-2.0 license described below.
- `--engine border` is a no-model fallback for a provably limited-palette,
  border-connected background, including a checkerboard baked into the image.
  It is not suitable for photographs. If the border is too varied, it refuses
  instead of guessing.
- `--engine auto` preserves already-meaningful alpha. An explicit `--engine
  rembg` or `--engine border` forces processing even when the input has alpha.

Output must be PNG or WebP. Inspect on black and white backgrounds before
shipping. X flattens alpha; Telegram inline photos may be converted, so send a
transparent PNG as a document/zip when the recipient needs the original alpha.

## Advanced mask workflow

If a decorated image defeats segmentation but a clean version of the same
shape exists, remove the clean variant's background, fill holes in that alpha
mask, verify alignment with a translucent overlay, and apply the mask to the
decorated variant. Never apply an interactively tuned mask before reviewing the
overlay on the target.

## Technique and licensing provenance

- Codex's bundled `imagegen` skill is Apache-2.0 and provides
  `scripts/remove_chroma_key.py`: Pillow border/corner key sampling, hard or
  soft mattes, key-colour despill, alpha contraction, feathering, and alpha
  counts. This plugin independently implements the relevant border sampling,
  alpha verification, and one-to-two-pixel contraction techniques; it does not
  copy the bundled source.
- [rembg](https://github.com/danielgatis/rembg) supplies the local neural
  segmentation engine under the [MIT license](https://github.com/danielgatis/rembg/blob/main/LICENSE.txt).
- `u2net` and `u2netp` are the only allowed model weights. Both come from the
  [U²-Net project](https://github.com/xuebinqin/U-2-Net), whose weights and code
  are [Apache-2.0](https://github.com/xuebinqin/U-2-Net/blob/master/LICENSE).
  rembg pins the downloads and checksums in its
  [`u2net` session](https://github.com/danielgatis/rembg/blob/main/rembg/sessions/u2net.py)
  (`md5:60024c5c889badc19c04ad937298a77b`) and
  [`u2netp` session](https://github.com/danielgatis/rembg/blob/main/rembg/sessions/u2netp.py)
  (`md5:8e83ca70e441ab06c318d82300c84806`).
- rembg's `bria-rmbg` weights are **blocked** because its
  [upstream model table](https://github.com/danielgatis/rembg#models) says
  commercial use requires a paid BRIA agreement. `withoutbg` is blocked because
  it is a cloud API. All other rembg models remain outside the allow-list until
  their downloadable weight licenses are recorded here.
