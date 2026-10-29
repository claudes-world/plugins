#!/usr/bin/env python3
"""vnc-computer: stdio MCP server that drives a remote desktop over VNC (RFB).

Minimal MCP (JSON-RPC 2.0, newline-delimited) implementation: initialize,
ping, tools/list, tools/call. Screenshots are returned as PNG image content.
All model-facing coordinates are in screenshot-image pixels; they are mapped
back to full framebuffer resolution before being sent to the VNC server.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_VENV = os.path.join(HERE, '.venv')
if (__name__ == '__main__' and os.path.exists(os.path.join(_VENV, 'bin', 'python3'))
        and os.path.realpath(sys.prefix) != os.path.realpath(_VENV)
        and not os.environ.get('VNC_COMPUTER_NO_VENV')):
    # Optional plugin-local venv from bin/setup (adds Pillow on bare hosts).
    os.execv(os.path.join(_VENV, 'bin', 'python3'),
             [os.path.join(_VENV, 'bin', 'python3'), os.path.abspath(__file__)] + sys.argv[1:])

import base64  # noqa: E402
import datetime  # noqa: E402
import json  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402

from vnclib import keys as keymap  # noqa: E402
from vnclib.imaging import MAX_LONG_EDGE, crop, default_scale, encode_png, have_pillow, scaled_size  # noqa: E402
from vnclib.recorder import Recorder  # noqa: E402
from vnclib.rfb import (BUTTON_LEFT, BUTTON_MIDDLE, BUTTON_RIGHT, DEFAULT_ENCODINGS,  # noqa: E402
                        WHEEL, RFBClient, RFBError)

VERSION = '0.1.0'
DEFAULT_ALLOW = '127.0.0.1,localhost,::1'


def log(msg):
    stamp = time.strftime('%H:%M:%S')
    sys.stderr.write('[vnc-computer %s] %s\n' % (stamp, msg))
    sys.stderr.flush()


class ToolError(Exception):
    pass


class Config:
    def __init__(self, env=None):
        env = os.environ if env is None else env
        self.host = env.get('VNC_HOST', '').strip()
        self.port = int(env.get('VNC_PORT', '5900') or 5900)
        self.password_file = env.get('VNC_PASSWORD_FILE', '').strip()
        self.username = env.get('VNC_USERNAME', '').strip() or None
        self.allow = [h.strip().lower() for h in env.get('VNC_ALLOW_HOSTS', DEFAULT_ALLOW).split(',') if h.strip()]
        self.scale = env.get('VNC_SCALE', '').strip() or None
        self.settle = int(env.get('VNC_SETTLE_MS', '400') or 400) / 1000.0
        self.max_fps = float(env.get('VNC_MAX_FPS', '20') or 20)
        self.type_delay = int(env.get('VNC_TYPE_DELAY_MS', '8') or 8) / 1000.0
        self.encodings = [e.strip().lower() for e in env.get('VNC_ENCODINGS', ','.join(DEFAULT_ENCODINGS)).split(',') if e.strip()]
        self.record_dir = os.path.expanduser(env.get('VNC_RECORD_DIR', '~/vnc-recordings'))
        self.draw_cursor = env.get('VNC_DRAW_CURSOR', '1') not in ('0', 'false', 'no')

    def check(self):
        if not self.host:
            raise ToolError('VNC_HOST is not set; refusing to connect anywhere.')
        if self.host.lower() not in self.allow:
            raise ToolError('VNC_HOST %s is not in VNC_ALLOW_HOSTS (%s); refusing to connect.'
                            % (self.host, ','.join(self.allow)))
        if self.scale is not None:
            default_scale(1, 1, self.scale)  # validates range

    def read_password(self):
        if not self.password_file:
            return None
        path = os.path.expanduser(self.password_file)
        try:
            st = os.stat(path)
            with open(path, 'rb') as fh:
                data = fh.read()
        except OSError as exc:
            raise ToolError('cannot read VNC_PASSWORD_FILE: %s' % exc.strerror)
        if st.st_mode & 0o077:
            log('warning: password file is group/world readable; chmod 600 it')
        return data.rstrip(b'\r\n')


class Session:
    def __init__(self, config):
        self.cfg = config
        self._client = None
        self._lock = threading.RLock()
        self.recorder = None

    # -------------------------------------------------------- connection
    def client(self):
        with self._lock:
            if self._client is not None and not self._client.closed:
                return self._client
            if self._client is not None:
                log('reconnecting (previous connection: %s)' % (self._client.error or 'closed'))
            self.cfg.check()
            password = self.cfg.read_password()
            log('connecting to %s:%d' % (self.cfg.host, self.cfg.port))
            c = RFBClient(self.cfg.host, self.cfg.port, password=password, username=self.cfg.username,
                          max_fps=self.cfg.max_fps, encodings=self.cfg.encodings, log=log)
            try:
                c.connect()
            except (OSError, RFBError) as exc:
                raise ToolError('VNC connection to %s:%d failed: %s' % (self.cfg.host, self.cfg.port, exc))
            self._client = c
            return c

    def scale(self, c):
        return default_scale(c.width, c.height, self.cfg.scale)

    def to_full(self, c, x, y):
        s = self.scale(c)
        return float(x) / s, float(y) / s

    def to_image(self, c, x, y):
        s = self.scale(c)
        return round(x * s), round(y * s)

    # -------------------------------------------------------- screenshots
    def screenshot(self, note=None):
        c = self.client()
        c.wait_idle(3.0)
        w, h, rgb = c.snapshot(draw_cursor=self.cfg.draw_cursor)
        s = self.scale(c)
        out = scaled_size(w, h, s)
        png = encode_png(rgb, w, h, out_size=out)
        meta = {'display_width': w, 'display_height': h, 'image_width': out[0], 'image_height': out[1],
                'scale': round(s, 6), 'coordinates': 'image pixels (mapped to display by /scale)'}
        if c.pointer_pos:
            meta['pointer'] = list(self.to_image(c, *c.pointer_pos))
        if self.recorder:
            meta['recording'] = self.recorder.out_dir
        text = (note + '\n' if note else '') + json.dumps(meta)
        return [{'type': 'image', 'data': base64.b64encode(png).decode('ascii'), 'mimeType': 'image/png'},
                {'type': 'text', 'text': text}]

    def settle_then_screenshot(self, note=None):
        time.sleep(self.cfg.settle)
        return self.screenshot(note)

    # -------------------------------------------------------- input helpers
    def _hold(self, c, syms, down):
        for sym in (syms if down else reversed(syms)):
            c.key(sym, down)

    def click(self, x, y, button, count=1, modifiers=''):
        c = self.client()
        fx, fy = self.to_full(c, x, y)
        mods = [s for combo in keymap.parse_sequence(modifiers) for s in combo] if modifiers.strip() else []
        c.pointer(fx, fy, 0)
        time.sleep(0.03)
        self._hold(c, mods, True)
        for i in range(count):
            c.pointer(fx, fy, button)
            time.sleep(0.04)
            c.pointer(fx, fy, 0)
            if i + 1 < count:
                time.sleep(0.07)
        self._hold(c, mods, False)

    def type_text(self, text):
        c = self.client()
        for held, sym in keymap.text_plan(text):
            self._hold(c, held, True)
            c.key(sym, True)
            c.key(sym, False)
            self._hold(c, held, False)
            if self.cfg.type_delay:
                time.sleep(self.cfg.type_delay)

    def press_keys(self, keys, repeat=1):
        c = self.client()
        try:
            seq = keymap.parse_sequence(keys)
        except ValueError as exc:
            raise ToolError(str(exc))
        for _ in range(max(1, int(repeat))):
            for combo in seq:
                self._hold(c, combo, True)
                time.sleep(0.02)
                self._hold(c, combo, False)
                time.sleep(0.03)


def _num(args, name, default=None):
    if name not in args or args[name] is None:
        if default is None:
            raise ToolError('missing required argument: %s' % name)
        return default
    try:
        return float(args[name])
    except (TypeError, ValueError):
        raise ToolError('argument %s must be a number' % name)


XY = {'x': {'type': 'number', 'description': 'X in screenshot-image pixels'},
      'y': {'type': 'number', 'description': 'Y in screenshot-image pixels'}}
MODS = {'modifiers': {'type': 'string', 'description': 'Optional keys held during the click, e.g. "cmd" or "shift+alt"'}}


def _schema(props=None, required=()):
    return {'type': 'object', 'properties': props or {}, 'required': list(required), 'additionalProperties': False}


TOOLS = [
    ('screenshot', 'Capture the remote screen. Returns a PNG plus display size and scale. '
                   'All other tools take coordinates in this image\'s pixel space.', _schema()),
    ('left_click', 'Move to (x, y) and left-click. Returns a fresh screenshot.',
     _schema(dict(XY, **MODS), ['x', 'y'])),
    ('right_click', 'Move to (x, y) and right-click. Returns a fresh screenshot.',
     _schema(dict(XY, **MODS), ['x', 'y'])),
    ('middle_click', 'Move to (x, y) and middle-click. Returns a fresh screenshot.',
     _schema(dict(XY, **MODS), ['x', 'y'])),
    ('double_click', 'Move to (x, y) and double-click (left). Returns a fresh screenshot.',
     _schema(dict(XY, **MODS), ['x', 'y'])),
    ('move', 'Move the pointer to (x, y) without clicking (hover). Returns a fresh screenshot.',
     _schema(XY, ['x', 'y'])),
    ('drag', 'Press the left button at (x1, y1), move to (x2, y2) in steps, release. Returns a fresh screenshot.',
     _schema({'x1': {'type': 'number'}, 'y1': {'type': 'number'}, 'x2': {'type': 'number'},
              'y2': {'type': 'number'},
              'duration_ms': {'type': 'integer', 'description': 'Drag duration, default 300'}},
             ['x1', 'y1', 'x2', 'y2'])),
    ('type', 'Type text with key events (US layout; Shift added for capitals/symbols; \\n = Return). '
             'Returns a fresh screenshot.',
     _schema({'text': {'type': 'string'}}, ['text'])),
    ('key', 'Press a key or chord, xdotool style: "Return", "Tab", "Escape", "cmd+l", "ctrl+c", '
            '"shift+Tab", "Page_Down". Space-separate several: "ctrl+a Delete". cmd/super = Command on macOS, '
            'alt = Option. Returns a fresh screenshot.',
     _schema({'keys': {'type': 'string'}, 'repeat': {'type': 'integer', 'description': 'Times to repeat, default 1'}},
             ['keys'])),
    ('scroll', 'Scroll at (x, y) with mouse-wheel clicks. Returns a fresh screenshot.',
     _schema(dict(XY, direction={'type': 'string', 'enum': ['up', 'down', 'left', 'right']},
                  amount={'type': 'integer', 'description': 'Wheel clicks, default 3'}), ['x', 'y', 'direction'])),
    ('wait', 'Wait, then return a fresh screenshot (for page loads / streaming output).',
     _schema({'ms': {'type': 'integer', 'description': 'Milliseconds, default 1000, max 60000'}})),
    ('zoom', 'Return a full-resolution crop of the region (x, y, w, h), given in screenshot-image pixels, '
             'to read small text.',
     _schema(dict(XY, w={'type': 'number'}, h={'type': 'number'}), ['x', 'y', 'w', 'h'])),
    ('record_start', 'Start saving framebuffer PNGs at a fixed interval in a background thread, '
                     'with frames.jsonl (timestamp, path). Frames are assembled into video elsewhere.',
     _schema({'interval_ms': {'type': 'integer', 'description': 'Capture interval, default 200 (5 fps)'},
              'out_dir': {'type': 'string', 'description': 'Output directory, default $VNC_RECORD_DIR/<timestamp>'},
              'scale': {'type': 'number', 'description': 'Frame scale (0,1], default 1.0 (full resolution)'}})),
    ('record_stop', 'Stop recording; returns frame count, duration and the frames.jsonl path.', _schema()),
]


def call_tool(session, name, args):
    c_action = None
    if name == 'screenshot':
        return session.screenshot()
    if name in ('left_click', 'right_click', 'middle_click', 'double_click'):
        x, y = _num(args, 'x'), _num(args, 'y')
        button = {'right_click': BUTTON_RIGHT, 'middle_click': BUTTON_MIDDLE}.get(name, BUTTON_LEFT)
        session.click(x, y, button, 2 if name == 'double_click' else 1, args.get('modifiers') or '')
        c_action = '%s x=%d y=%d%s' % (name, x, y, ' mods=%s' % args['modifiers'] if args.get('modifiers') else '')
    elif name == 'move':
        x, y = _num(args, 'x'), _num(args, 'y')
        c = session.client()
        c.pointer(*session.to_full(c, x, y))
        c_action = 'move x=%d y=%d' % (x, y)
    elif name == 'drag':
        x1, y1, x2, y2 = (_num(args, k) for k in ('x1', 'y1', 'x2', 'y2'))
        duration = max(0.0, _num(args, 'duration_ms', 300) / 1000.0)
        c = session.client()
        fx1, fy1 = session.to_full(c, x1, y1)
        fx2, fy2 = session.to_full(c, x2, y2)
        c.pointer(fx1, fy1, 0)
        time.sleep(0.03)
        c.pointer(fx1, fy1, BUTTON_LEFT)
        steps = max(2, int(duration / 0.015))
        for i in range(1, steps + 1):
            t = i / steps
            c.pointer(fx1 + (fx2 - fx1) * t, fy1 + (fy2 - fy1) * t, BUTTON_LEFT)
            time.sleep(duration / steps)
        c.pointer(fx2, fy2, 0)
        c_action = 'drag %d,%d -> %d,%d' % (x1, y1, x2, y2)
    elif name == 'type':
        text = args.get('text')
        if not isinstance(text, str):
            raise ToolError('missing required argument: text')
        session.type_text(text)
        c_action = 'type len=%d' % len(text)  # never log typed content
    elif name == 'key':
        keys = args.get('keys')
        if not isinstance(keys, str) or not keys.strip():
            raise ToolError('missing required argument: keys')
        session.press_keys(keys, args.get('repeat') or 1)
        c_action = 'key %s' % keys
    elif name == 'scroll':
        x, y = _num(args, 'x'), _num(args, 'y')
        direction = args.get('direction')
        if direction not in WHEEL:
            raise ToolError('direction must be one of up/down/left/right')
        amount = max(1, min(50, int(_num(args, 'amount', 3))))
        c = session.client()
        fx, fy = session.to_full(c, x, y)
        c.pointer(fx, fy, 0)
        for _ in range(amount):
            c.pointer(fx, fy, WHEEL[direction])
            c.pointer(fx, fy, 0)
            time.sleep(0.02)
        c_action = 'scroll %s x%d at %d,%d' % (direction, amount, x, y)
    elif name == 'wait':
        ms = max(0, min(60000, int(_num(args, 'ms', 1000))))
        session.client()
        time.sleep(ms / 1000.0)
        log('wait %dms' % ms)
        return session.screenshot()
    elif name == 'zoom':
        x, y, w, h = (_num(args, k) for k in ('x', 'y', 'w', 'h'))
        c = session.client()
        c.wait_idle(3.0)
        fx, fy = session.to_full(c, x, y)
        fw, fh = session.to_full(c, w, h)
        W, H, rgb = c.snapshot(draw_cursor=session.cfg.draw_cursor)
        part, cw, ch = crop(rgb, W, H, fx, fy, fw, fh)
        s = min(1.0, MAX_LONG_EDGE / max(cw, ch))
        out = scaled_size(cw, ch, s)
        png = encode_png(part, cw, ch, out_size=out)
        log('zoom %d,%d %dx%d' % (x, y, w, h))
        return [{'type': 'image', 'data': base64.b64encode(png).decode('ascii'), 'mimeType': 'image/png'},
                {'type': 'text', 'text': json.dumps({'display_region': [int(fx), int(fy), cw, ch],
                                                     'image_width': out[0], 'image_height': out[1],
                                                     'zoom_scale': round(s, 6)})}]
    elif name == 'record_start':
        if session.recorder:
            raise ToolError('already recording to %s' % session.recorder.out_dir)
        interval = int(_num(args, 'interval_ms', 200))
        scale = _num(args, 'scale', 1.0)
        if not 0 < scale <= 1:
            raise ToolError('scale must be in (0, 1]')
        out_dir = args.get('out_dir') or os.path.join(
            session.cfg.record_dir, datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
        out_dir = os.path.expanduser(out_dir)
        session.client()

        def grab():
            return session.client().snapshot(draw_cursor=session.cfg.draw_cursor)
        try:
            session.recorder = Recorder(grab, out_dir, interval, scale, log=log).start()
        except OSError as exc:
            raise ToolError('cannot start recording: %s' % exc)
        log('record_start %s every %dms' % (session.recorder.out_dir, interval))
        return [{'type': 'text', 'text': json.dumps({'recording': True, 'out_dir': session.recorder.out_dir,
                                                     'interval_ms': interval, 'scale': scale})}]
    elif name == 'record_stop':
        if not session.recorder:
            raise ToolError('not recording')
        rec, session.recorder = session.recorder, None
        summary = rec.stop()
        log('record_stop %d frames (%d dropped) in %s' % (summary['frames'], summary['dropped'], rec.out_dir))
        return [{'type': 'text', 'text': json.dumps(summary)}]
    else:
        raise ToolError('unknown tool: %s' % name)
    log(c_action)
    return session.settle_then_screenshot()


# ------------------------------------------------------------ JSON-RPC --
class Server:
    def __init__(self, session, out=None):
        self.session = session
        self.out = out or sys.stdout

    def send(self, msg):
        self.out.write(json.dumps(msg, separators=(',', ':')) + '\n')
        self.out.flush()

    def handle(self, msg):
        method, mid = msg.get('method'), msg.get('id')
        if method is None or mid is None:
            return None  # notification or response: nothing to answer
        params = msg.get('params') or {}
        if method == 'initialize':
            result = {'protocolVersion': params.get('protocolVersion') or '2025-06-18',
                      'capabilities': {'tools': {'listChanged': False}},
                      'serverInfo': {'name': 'vnc-computer', 'version': VERSION},
                      'instructions': ('Drive a remote desktop over VNC. Call screenshot first; every '
                                       'action returns a fresh screenshot. Coordinates are screenshot-image '
                                       'pixels. Use zoom to read small text.')}
        elif method == 'ping':
            result = {}
        elif method == 'tools/list':
            result = {'tools': [{'name': n, 'description': d, 'inputSchema': s} for n, d, s in TOOLS]}
        elif method == 'tools/call':
            name, args = params.get('name'), params.get('arguments') or {}
            try:
                result = {'content': call_tool(self.session, name, args), 'isError': False}
            except ToolError as exc:
                log('%s failed: %s' % (name, exc))
                result = {'content': [{'type': 'text', 'text': str(exc)}], 'isError': True}
            except (OSError, RFBError) as exc:
                log('%s failed: %s' % (name, exc))
                result = {'content': [{'type': 'text', 'text': 'VNC error: %s' % exc}], 'isError': True}
        else:
            return {'jsonrpc': '2.0', 'id': mid, 'error': {'code': -32601, 'message': 'method not found: %s' % method}}
        return {'jsonrpc': '2.0', 'id': mid, 'result': result}

    def serve(self, inp=None):
        inp = inp or sys.stdin
        log('ready (pillow=%s, venv=%s, host=%s)' % (have_pillow(), sys.prefix != sys.base_prefix,
                                                     self.session.cfg.host or 'UNSET'))
        for line in inp:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                self.send({'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'parse error'}})
                continue
            try:
                reply = self.handle(msg)
            except Exception as exc:  # keep serving on unexpected bugs
                log('internal error: %r' % exc)
                reply = {'jsonrpc': '2.0', 'id': msg.get('id'), 'error': {'code': -32603, 'message': str(exc)}}
            if reply is not None:
                self.send(reply)
        if self.session.recorder:
            self.session.recorder.stop()


def check_connection(path):
    """CLI: connect with the VNC_* env, save one screenshot to path, print metadata."""
    session = Session(Config())
    try:
        content = session.screenshot()
    except (ToolError, OSError, RFBError) as exc:
        log('check failed: %s' % exc)
        return 1
    with open(path, 'wb') as fh:
        fh.write(base64.b64decode(content[0]['data']))
    print(content[1]['text'])
    print('wrote %s' % path)
    session.client().close()
    return 0


def main(argv):
    if len(argv) == 3 and argv[1] == '--screenshot':
        return check_connection(argv[2])
    if len(argv) > 1:
        sys.stderr.write('usage: server.py              (stdio MCP server)\n'
                         '       server.py --screenshot OUT.png   (connection check)\n')
        return 2
    Server(Session(Config())).serve()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
