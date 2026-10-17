#!/usr/bin/env python3
"""End-to-end smoke test: test rig (Xvfb + x11vnc + Chrome) <-> server.py over MCP stdio.

Run: python3 test/smoke.py   (needs Xvfb, x11vnc, google-chrome, Pillow)
Set VNC_SMOKE_KEEP_RIG=1 to leave the rig running afterwards and
VNC_SMOKE_KEEP_ARTIFACTS=1 to keep the screenshots/recording on success.
"""
import base64
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

from PIL import Image

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RIG = os.path.join(PLUGIN, 'bin', 'test-rig')
PAGE_URL = 'file://' + os.path.join(PLUGIN, 'test', 'page.html')
RED, GREEN = (200, 40, 40), (30, 160, 70)
PROBE = (1000, 650)  # page background, right of the toggle button (full-res px)
BUTTON = (320, 400)  # inside the toggle button for any browser-chrome height 0..300

results = []


def check(name, cond, detail=''):
    results.append((name, bool(cond)))
    print('%s  %s%s' % ('PASS' if cond else 'FAIL', name, (' -- ' + detail) if detail else ''), flush=True)
    return cond


def close(a, b, tol=12):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


class MCP:
    def __init__(self, env, stderr_path):
        self.stderr = open(stderr_path, 'w')
        self.proc = subprocess.Popen([sys.executable, os.path.join(PLUGIN, 'server.py')], env=env,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr,
                                     text=True, bufsize=1)
        self.next_id = 0

    def request(self, method, params=None):
        self.next_id += 1
        self.proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': self.next_id, 'method': method,
                                          'params': params or {}}) + '\n')
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError('server exited (see stderr log)')
        msg = json.loads(line)
        assert msg['id'] == self.next_id, msg
        if 'error' in msg:
            raise RuntimeError(msg['error'])
        return msg['result']

    def notify(self, method):
        self.proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'method': method}) + '\n')
        self.proc.stdin.flush()

    def tool(self, name, **args):
        res = self.request('tools/call', {'name': name, 'arguments': args})
        if res.get('isError'):
            raise RuntimeError('%s: %s' % (name, res['content'][0]['text']))
        img = meta = None
        for block in res['content']:
            if block['type'] == 'image':
                img = Image.open(io.BytesIO(base64.b64decode(block['data']))).convert('RGB')
            elif block['type'] == 'text':
                meta = json.loads(block['text'].splitlines()[-1])
        return img, meta

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=30)
        self.stderr.close()


def diff_fraction(a, b):
    a, b = a.tobytes(), b.tobytes()
    changed = sum(1 for i in range(0, len(a), 3 * 7) if a[i:i + 3] != b[i:i + 3])
    return changed / (len(a) // (3 * 7))


def wait_for_color(mcp, xy, color, scale=1.0, tries=6):
    img = None
    for _ in range(tries):
        img, _ = mcp.tool('wait', ms=300)
        px = img.getpixel((round(xy[0] * scale), round(xy[1] * scale)))
        if close(px, color):
            return img, px
    return img, img.getpixel((round(xy[0] * scale), round(xy[1] * scale)))


def main():
    work = tempfile.mkdtemp(prefix='vnc-smoke-')
    out = subprocess.run([RIG, 'start'], capture_output=True, text=True, timeout=90)
    if out.returncode != 0:
        print(out.stderr)
        check('test rig starts', False)
        return 1
    rig_env = dict(line.split('=', 1) for line in out.stdout.split() if '=' in line)
    check('test rig starts', True, out.stderr.strip().splitlines()[-1])
    password = open(rig_env['VNC_PASSWORD_FILE']).read().strip()
    env = dict(os.environ, **rig_env, VNC_SETTLE_MS='400', VNC_RECORD_DIR=os.path.join(work, 'rec'))
    stderr_log = os.path.join(work, 'server.stderr')
    mcp = MCP(env, stderr_log)
    try:
        init = mcp.request('initialize', {'protocolVersion': '2025-06-18', 'capabilities': {},
                                          'clientInfo': {'name': 'smoke', 'version': '0'}})
        mcp.notify('notifications/initialized')
        check('initialize', init['serverInfo']['name'] == 'vnc-computer')
        names = {t['name'] for t in mcp.request('tools/list')['tools']}
        want = {'screenshot', 'left_click', 'right_click', 'double_click', 'move', 'drag', 'type', 'key',
                'scroll', 'wait', 'zoom', 'record_start', 'record_stop'}
        check('tools/list has all tools', want <= names, ', '.join(sorted(want - names)))

        time.sleep(2)  # let Chrome finish its first paint
        before, meta = mcp.tool('screenshot')
        check('screenshot returns PNG at display size', before.size == (1280, 800) and meta['scale'] == 1.0,
              '%s scale=%s' % (before.size, meta['scale']))

        mcp.tool('move', x=640, y=60)
        mcp.tool('key', keys='ctrl+l')
        mcp.tool('type', text=PAGE_URL)
        mcp.tool('key', keys='Return')
        after, px = wait_for_color(mcp, PROBE, RED)
        frac = diff_fraction(before, after)
        check('URL typed into omnibox changes the screen', frac > 0.2, 'changed %.0f%% of sampled pixels' % (frac * 100))
        check('test page loaded (red background at probe)', close(px, RED), 'pixel %s' % (px,))

        mcp.tool('left_click', x=BUTTON[0], y=BUTTON[1])
        _, px = wait_for_color(mcp, PROBE, GREEN)
        check('left_click on button turns background green', close(px, GREEN), 'pixel %s' % (px,))

        rec_dir = os.path.join(work, 'rec', 'run1')
        _, meta = mcp.tool('record_start', interval_ms=200, out_dir=rec_dir)
        time.sleep(2.0)
        _, summary = mcp.tool('record_stop')
        pngs = sorted(f for f in os.listdir(rec_dir) if f.endswith('.png'))
        lines = open(os.path.join(rec_dir, 'frames.jsonl')).read().splitlines()
        first = json.loads(lines[0]) if lines else {}
        ok_png = bool(pngs) and Image.open(os.path.join(rec_dir, pngs[0])).size == (1280, 800)
        check('record 2s -> >=3 PNG frames + frames.jsonl', len(pngs) >= 3 and len(lines) == len(pngs) and ok_png
              and os.path.exists(first.get('path', '')),
              '%d frames, %d index lines, %d dropped' % (len(pngs), len(lines), summary['dropped']))
        cat = subprocess.run([os.path.join(PLUGIN, 'bin', 'frames-concat'), rec_dir], capture_output=True, text=True)
        listed = open(os.path.join(rec_dir, 'concat.txt')).read().count("file '") if cat.returncode == 0 else 0
        check('frames-concat writes an ffmpeg concat list', listed == len(pngs) + 1, cat.stdout.strip())
    finally:
        mcp.close()

    # Second server instance with downscaling: coordinates must map back.
    env_scaled = dict(env, VNC_SCALE='0.5')
    mcp = MCP(env_scaled, stderr_log + '.scaled')
    try:
        mcp.request('initialize', {'protocolVersion': '2025-06-18'})
        img, meta = mcp.tool('screenshot')
        check('VNC_SCALE=0.5 screenshot is 640x400', img.size == (640, 400) and meta['display_width'] == 1280,
              '%s %s' % (img.size, meta))
        mcp.tool('left_click', x=BUTTON[0] / 2, y=BUTTON[1] / 2)
        img, px = wait_for_color(mcp, PROBE, RED, scale=0.5)
        check('scaled click maps to full-res button (toggles back to red)', close(px, RED), 'pixel %s' % (px,))
        zimg, zmeta = mcp.tool('zoom', x=PROBE[0] / 2 - 20, y=PROBE[1] / 2 - 20, w=40, h=40)
        errors = []
        for name, args in (('right_click', {'x': 500, 'y': 325}), ('key', {'keys': 'Escape'}),
                           ('double_click', {'x': 500, 'y': 325}), ('middle_click', {'x': 500, 'y': 325}),
                           ('scroll', {'x': 500, 'y': 325, 'direction': 'down', 'amount': 2}),
                           ('drag', {'x1': 450, 'y1': 300, 'x2': 550, 'y2': 350, 'duration_ms': 150})):
            try:
                img, _ = mcp.tool(name, **args)
                if img is None or img.size != (640, 400):
                    errors.append('%s: no screenshot' % name)
            except RuntimeError as exc:
                errors.append(str(exc))
        check('right/double/middle click, scroll, drag, Escape all return screenshots', not errors, '; '.join(errors))
        check('zoom returns full-res crop', zimg.size == (80, 80) and close(zimg.getpixel((40, 40)), RED),
              '%s %s' % (zimg.size, zmeta))
    finally:
        mcp.close()

    logs = open(stderr_log).read() + open(stderr_log + '.scaled').read()
    check('stderr log has actions but no password or typed text',
          'left_click' in logs and password not in logs and PAGE_URL not in logs)

    if not os.environ.get('VNC_SMOKE_KEEP_RIG'):
        subprocess.run([RIG, 'stop'], capture_output=True, timeout=60)
    passed = sum(ok for _, ok in results)
    if passed == len(results) and not os.environ.get('VNC_SMOKE_KEEP_ARTIFACTS'):
        shutil.rmtree(work, ignore_errors=True)
        where = 'artifacts removed'
    else:
        where = 'artifacts: %s' % work
    print('SUMMARY: %d/%d checks passed (%s)' % (passed, len(results), where))
    return 0 if passed == len(results) else 1


if __name__ == '__main__':
    sys.exit(main())
