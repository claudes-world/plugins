# vnc-computer

VNC remote desktop **computer use** for Claude Code. This stdio MCP server lets an
agent see and drive any VNC/RFB desktop (macOS Screen Sharing, x11vnc,
TigerVNC). It can screenshot, click, type, send key chords, scroll, drag and
zoom, and it can record the screen to timestamped PNG frames so a video can be
assembled on another machine.

It is pure Python 3 standard library: the RFB client, VNC/Apple authentication,
ZRLE/Zlib decoding, PNG encoding and MCP protocol are all implemented here.
Pillow is used when present for smoother downscaling. Nothing is vendored.

## Setup

1. Enable the plugin. `.mcp.json` starts `python3 ${CLAUDE_PLUGIN_ROOT}/server.py`.
2. Optional: run `bin/setup` to create a plugin-local `.venv` (system site
   packages, plus Pillow if the system Python lacks it). When `.venv` exists,
   `server.py` re-executes itself with it. Nothing is installed system-wide.
3. Export the `VNC_*` variables below in the environment that launches Claude
   Code, or put them in that agent's settings `env`. The MCP server inherits
   them.
4. Check the connection without MCP:
   `python3 server.py --screenshot /tmp/check.png`.

The server connects lazily on the first tool call and reconnects automatically
if the connection drops.

## Environment

| Variable | Default | Meaning |
|---|---|---|
| `VNC_HOST` | (required) | Server address. With no host set, every tool refuses to run. |
| `VNC_PORT` | `5900` | RFB port. |
| `VNC_ALLOW_HOSTS` | `127.0.0.1,localhost,::1` | Comma-separated allowlist. `VNC_HOST` must match an entry exactly. Example: `192.0.2.10` (the macOS host's private or tailnet address). |
| `VNC_PASSWORD_FILE` | unset | Path to a file holding the password (one line, `chmod 600`). The password is never read from the environment and never logged. Classic VNC auth uses only the first 8 characters. |
| `VNC_USERNAME` | unset | macOS account name. When set, Apple Remote Desktop auth (type 30) is preferred and uses the macOS account password from `VNC_PASSWORD_FILE`. |
| `VNC_SCALE` | auto | Screenshot scale factor in (0, 1]. By default the long edge is at most 1568 px (1920x1080 becomes 1568x882). Click coordinates are mapped back to full resolution. |
| `VNC_SETTLE_MS` | `400` | Delay after each action before the returned screenshot. |
| `VNC_TYPE_DELAY_MS` | `8` | Delay between typed characters. |
| `VNC_MAX_FPS` | `20` | Maximum framebuffer refresh rate requested from the server. |
| `VNC_ENCODINGS` | `zrle,copyrect,zlib,raw` | Encoding preference. Use `raw` on a fast LAN if decoding becomes the bottleneck. |
| `VNC_CMD_KEYSYM` | `Super_L` | Keysym sent for `cmd`/`super`/`meta`. Set `Meta_L` if a server maps Command differently. |
| `VNC_RECORD_DIR` | `~/vnc-recordings` | Parent directory for `record_start` when no `out_dir` is given. |
| `VNC_DRAW_CURSOR` | `1` | Composite the server-provided cursor shape at the agent's pointer position into screenshots and frames. |

## Tools

All coordinates are in **screenshot-image pixels**: the image the model saw.
Every action returns a fresh screenshot after `VNC_SETTLE_MS`.

| Tool | Arguments |
|---|---|
| `screenshot` | none. Returns PNG + JSON (display size, image size, scale, pointer). |
| `left_click`, `right_click`, `middle_click`, `double_click` | `x`, `y`, optional `modifiers` (`"cmd"`, `"shift+alt"`) |
| `move` | `x`, `y` (hover) |
| `drag` | `x1`, `y1`, `x2`, `y2`, optional `duration_ms` (300) |
| `type` | `text`. US layout; Shift is added for capitals and symbols; `\n` sends Return. |
| `key` | `keys`, xdotool style: `Return`, `Tab`, `Escape`, `cmd+l`, `ctrl+c`, `shift+Tab`, `Page_Down`, `F5`. Space-separate a sequence: `"ctrl+a Delete"`. Optional `repeat`. `cmd`/`super` = Command, `alt`/`option` = Option. |
| `scroll` | `x`, `y`, `direction` (`up`/`down`/`left`/`right`), `amount` (wheel clicks, 3) |
| `wait` | `ms` (1000, max 60000), then screenshot |
| `zoom` | `x`, `y`, `w`, `h` in image pixels. Returns a full-resolution crop for reading small text. |
| `record_start` | `interval_ms` (200), `out_dir`, `scale` (1.0) |
| `record_stop` | none. Returns frames, dropped, duration and the `frames.jsonl` path. |

Actions are logged to stderr. Logs never contain screenshots, typed text (only
its length) or the password.

## macOS recipe (Screen Sharing, e.g. a VM over a tailnet)

On the **Mac**:

1. System Settings -> General -> Sharing -> **Screen Sharing** on. Under (i),
   enable **"VNC viewers may control screen with password"** and set a password
   of 8 characters or fewer. This gives classic VNC auth (type 2), which is the
   tested path. Without that toggle, macOS offers only Apple auth; then set
   `VNC_USERNAME` to the macOS account and put that account's password in the
   password file (type 30, implemented but not yet tested against a real Mac).
2. Set the display to **1920x1080**. A VM's virtual display should be
   configured to 1080p, not Retina/HiDPI. Screenshots then arrive at 1568x882
   (scale 0.8167), and recordings are full 1080p.
3. Keep it awake during sessions (`caffeinate -dis` in a terminal) and use the
   US keyboard layout. `type` maps symbols for US layout.

On the **controlling host** (where the agent runs):

```bash
# password file: one line, owner-only
mkdir -p ~/.config/vnc-computer
install -m 600 /dev/null ~/.config/vnc-computer/mac.pass   # then write the password into it
export VNC_HOST=192.0.2.10 VNC_PORT=5900          # the Mac's address
export VNC_ALLOW_HOSTS=192.0.2.10
export VNC_PASSWORD_FILE=~/.config/vnc-computer/mac.pass
python3 "$PLUGIN_ROOT/server.py" --screenshot /tmp/mac.png   # connection check
```

Then launch the agent with the same environment. The server reports
`RFB 003.889` and uses 3.8 semantics. Use `cmd+l` to focus the browser address
bar, `cmd+t` for a new tab, and so on.

The Command key is sent as `Super_L`, which Apple's Screen Sharing is expected
to map to Command. This mapping has not yet been verified against a live Mac. If
`cmd+l` does nothing, set `VNC_CMD_KEYSYM=Meta_L` and restart the server.

## Recording -> video assembly

`record_start` captures the current framebuffer every `interval_ms` on a
background thread. It writes `frame_000000.png`, ... plus `frames.jsonl`,
with one line per frame: `{"frame", "t" (epoch seconds), "t_rel", "file",
"path", "width", "height"}`. `record_stop` adds `recording.json` with the
totals. The frame rate is bounded by `VNC_MAX_FPS` and the network. 200 ms
(5 fps) to 100 ms (10 fps) is a reasonable range. At 1080p, budget roughly
50-500 KB per frame depending on screen content; use `scale: 0.5` for long
sessions.

The plugin never encodes video, so the controlling host needs no ffmpeg (some
agent hosts forbid video encoding). Copy the directory to a media machine and
assemble the video there:

```bash
# on the controlling host (no ffmpeg involved): build the concat list with real timings
bin/frames-concat ~/vnc-recordings/20261017-210000
rsync -a ~/vnc-recordings/20261017-210000 media-host:recordings/

# on the media machine
cd recordings/20261017-210000
ffmpeg -f concat -safe 0 -i concat.txt -fps_mode cfr -r 30 \
       -c:v libx264 -pix_fmt yuv420p -crf 18 session.mp4
```

`concat.txt` holds each frame until the next frame's capture timestamp, so
dropped frames do not distort timing.

## Local test rig and tests

Host prerequisites (Debian/Ubuntu) for the rig only:
`sudo apt-get install -y xvfb x11vnc` (or `tigervnc-standalone-server` as an
alternative VNC server) plus Google Chrome at `/usr/bin/google-chrome`.
Pillow is needed for `test/smoke.py`.

```bash
bin/test-rig            # Xvfb :99 1280x800x24 + x11vnc on 127.0.0.1:5999 (VNC auth) + Chrome; prints VNC_* env
bin/test-rig status
bin/test-rig stop
python3 test/test_unit.py   # rig-free: crypto vectors, ZRLE, keys, PNG, config safety
python3 test/smoke.py       # end to end over MCP stdio against the rig
bun test marketplace-layout.test.ts
```

The smoke test starts the rig and talks to `server.py` over MCP stdio. It
loads `test/page.html` through the omnibox (`ctrl+l`, `type`, `Return`),
clicks the page's toggle button and checks the background color at known
coordinates. It repeats the click with `VNC_SCALE=0.5` to verify coordinate
mapping, exercises the other tools, records 2 s of frames, and checks that
logs contain no secrets. Overrides: `VNC_RIG_DISPLAY`, `VNC_RIG_PORT`,
`VNC_RIG_GEOMETRY`, `VNC_RIG_DIR`.

## Limits

- Security types: None, VNC auth (2) and Apple ARD (30). Apple's RSA-based
  types (33/35/36) are not supported. ARD is verified only through AES/DES
  test vectors, not against a live Mac.
- Encodings: Raw, CopyRect, Zlib, ZRLE, plus Cursor, DesktopSize and LastRect.
  No Tight/Hextile; servers fall back to what is offered. Decoding is pure
  Python: incremental updates are cheap, but a full-screen change at 1080p
  costs a few hundred ms of CPU.
- No audio, no clipboard sync, single connection per server process (shared
  session, so other viewers stay connected).
- Text input assumes a US keyboard layout. Non-ASCII characters are sent as
  Unicode keysyms, which servers may ignore.
- The composited cursor follows the agent's pointer. Pointer moves made by
  someone else at the remote console are not reflected unless the server draws
  the cursor into the framebuffer.

## License

Owned code is MIT licensed (`LICENSE`). See `THIRD_PARTY_NOTICES.md` and
`providers.json`.
