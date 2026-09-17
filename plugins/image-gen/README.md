# image-gen

General raster-image production for any lane: Codex built-in `image_gen`, local
procedural rendering and post-processing, SVG-to-img2img polish, and background
removal.

## Onboarding

Generative image work must use Codex's built-in `image_gen` tool. Google image
models and APIs are not supported. The plugin reads no
image-provider credentials.

The plugin ships a stdlib-only convenience wrapper around `codex exec` at
`${CLAUDE_PLUGIN_ROOT}/bin/gen-image`:

```bash
${CLAUDE_PLUGIN_ROOT}/bin/gen-image "editorial illustration of a night garden" --aspect 16:9 -o out.png
```

On hosts that already expose `gen-image` on `PATH`, use `gen-image` directly.
Run `${CLAUDE_PLUGIN_ROOT}/bin/gen-image --help` for aspect-ratio, timeout, and
output behavior. Provider/model flags are intentionally rejected.

When `image_gen` fails to return native alpha, the skill also ships a free local
rembg/U²-Net fallback at
`${CLAUDE_PLUGIN_ROOT}/skills/image-assets/scripts/bg-remove`. It never calls an
inference API; see the background-removal reference for setup and validation.

## Included skill

- `image-assets` — general generation, editing, SVG-to-img2img polish, and
  background-removal guidance.

## Standalone use and license

This directory is an independent plugin root. Enable it in your plugin host.
Owned code and content are MIT licensed; third-party terms remain in
`THIRD_PARTY_NOTICES.md`. Provider requirements are declared in `providers.json`.

Tests: install Pillow locally, then `bun test marketplace-layout.test.ts` and
`python3 test/test_bg_remove.py`. Tests use synthetic fixtures and a Codex stub;
no image generation account, model download or paid service is used.
