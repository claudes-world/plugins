---
name: image-assets
description: "Raster image generation and editing with Codex's built-in image_gen tool: illustrations, photos, blog heroes, video stills, thumbnails, posters, sprites, pixel art, palette quantisation, background removal, transparent cutouts, procedural rendering, and SVG-to-image polish. MUST read before creating, generating, or editing image assets."
user_invocable: true
argument-hint: "[generate|bg-remove] <asset description>"
---

# Image assets — produce and edit raster images


## ⛔ Built-in Codex image generation only

All generative image creation and editing uses Codex's built-in `image_gen`.
Do not call Google image APIs, read a host image-provider key, or substitute
another paid provider. If `image_gen` is unavailable, report that limitation.
Account access to Codex is needed for generation; local post-processing and
background removal require no paid service.

The bundled `${CLAUDE_PLUGIN_ROOT}/bin/gen-image` CLI is only a thin convenience
wrapper around `codex exec`; it has no image backend or credential handling of
its own. A host that exposes it on `PATH` can use `gen-image` directly.

| Mode | Read | When |
|---|---|---|
| **quick generate** | — (`${CLAUDE_PLUGIN_ROOT}/bin/gen-image --help`) | Straightforward raster images: `${CLAUDE_PLUGIN_ROOT}/bin/gen-image "<prompt>" --aspect 16:9 -o /absolute/path/out.png`. The wrapper dispatches only Codex `image_gen`. |
| **generate or edit** | `references/generate.md` | Direct `codex exec` from a Claude lane, targeted edits/recolours, and coordinate-exact procedural work. The reference carries the verified invocation and polling pattern: name `image_gen`, use an absolute output path, run detached but poll in the foreground with a deadline, run jobs sequentially, and stdin-pipe prompts when attaching `-i` images. |
| **bg-remove** | `references/background-removal.md` | When native generator alpha failed, use the bundled free local CLI for rembg/U²-Net or limited-palette removal, shadow retention, 1–2 px halo cleanup, and alpha verification. |

Local post-processing is unchanged: use Pillow or the existing project tooling
for pixelising, palette quantisation, resizing, compositing, and deterministic
coordinate-exact rendering. Those transformations are not alternative image
generators. Background removal continues to follow
`references/background-removal.md`.

## SVG → polish workflow

For technically-precise-but-pretty images (math diagrams, geometric heroes):
build the geometry as exact SVG → render to PNG → feed to codex image_gen
with `-i` (stdin-pipe prompt) and HARD keep-the-geometry constraints +
"atmosphere only" instructions. The model preserves lines/vertices/dots
faithfully while adding glow, grain, and light falloff — raw text-to-image
kept failing this same geometry even with vertex-level prompts. **Edit
budget:** quality degrades over cumulative edits of its own output — plan
on 1–2 edit turns (occasionally 5+ works) to get your changes while keeping
the rest true to the base; get the base image right BEFORE polishing.
