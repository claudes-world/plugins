"""Minimal synchronous RFB (VNC) 3.3/3.7/3.8 client, stdlib only.

Supports security types None (1), VNC Authentication (2) and Apple Remote
Desktop (30, Diffie-Hellman + AES-128, macOS user name + password), and the
Raw, CopyRect, Zlib and ZRLE encodings plus Cursor, DesktopSize and LastRect
pseudo-encodings. A background thread keeps an RGB framebuffer current by
always holding one incremental update request open (throttled to max_fps).
"""
import hashlib
import os
import socket
import struct
import threading
import time
import zlib

from .crypto import aes128_ecb_encrypt, vnc_auth_response

ENC_RAW, ENC_COPYRECT, ENC_ZLIB, ENC_ZRLE = 0, 1, 6, 16
ENC_CURSOR, ENC_DESKTOPSIZE, ENC_LASTRECT = -239, -223, -224
ENCODING_NAMES = {'raw': ENC_RAW, 'copyrect': ENC_COPYRECT, 'zlib': ENC_ZLIB, 'zrle': ENC_ZRLE}
DEFAULT_ENCODINGS = ('zrle', 'copyrect', 'zlib', 'raw')

SEC_NONE, SEC_VNC, SEC_ARD = 1, 2, 30

BUTTON_LEFT, BUTTON_MIDDLE, BUTTON_RIGHT = 1, 2, 4
WHEEL = {'up': 8, 'down': 16, 'left': 32, 'right': 64}


class RFBError(Exception):
    pass


class RFBClient:
    def __init__(self, host, port=5900, password=None, username=None,
                 timeout=15.0, max_fps=20.0, encodings=None, log=None):
        self.host, self.port = host, int(port)
        self._password = password
        self._username = username
        self.timeout = timeout
        self.min_interval = 1.0 / max(1.0, float(max_fps))
        self.encodings = [ENCODING_NAMES[e] for e in (encodings or DEFAULT_ENCODINGS)]
        self.log = log or (lambda msg: None)
        self.sock = None
        self._rfile = None
        self._send_lock = threading.Lock()
        self._fb_lock = threading.Lock()
        self._cond = threading.Condition()
        self._zlib_zrle = zlib.decompressobj()
        self._zlib_raw = zlib.decompressobj()
        self.width = self.height = 0
        self.fb = bytearray()
        self.name = ''
        self.frame_seq = 0
        self.updating = False
        self.closed = True
        self.error = None
        self.cursor = None  # (hot_x, hot_y, w, h, rgb bytes, mask bytes)
        self.pointer_pos = None
        self.buttons = 0
        self._last_request = 0.0
        self._reader = None

    # ------------------------------------------------------------ io ----
    def _recv(self, n):
        data = self._rfile.read(n)
        if data is None or len(data) < n:
            raise RFBError('connection closed by server')
        return data

    def _u8(self):
        return self._recv(1)[0]

    def _u16(self):
        return struct.unpack('>H', self._recv(2))[0]

    def _u32(self):
        return struct.unpack('>I', self._recv(4))[0]

    def _send(self, data):
        with self._send_lock:
            if self.sock is None:
                raise RFBError('not connected')
            self.sock.sendall(data)

    # ----------------------------------------------------- handshake ----
    def connect(self, first_frame_timeout=60.0):
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._rfile = self.sock.makefile('rb')
        try:
            self._handshake()
        except Exception:
            self.close()
            raise
        self.sock.settimeout(None)
        self.closed = False
        self._reader = threading.Thread(target=self._read_loop, name='rfb-reader', daemon=True)
        self._reader.start()
        self._request(incremental=False)
        if not self.wait_frame(0, first_frame_timeout):
            raise RFBError('no framebuffer received within %.0fs' % first_frame_timeout)
        return self

    def _handshake(self):
        banner = self._recv(12)
        if not banner.startswith(b'RFB '):
            raise RFBError('not an RFB server: %r' % banner)
        major, minor = int(banner[4:7]), int(banner[8:11])
        # Apple advertises 3.889; it speaks 3.8 to standard clients.
        minor = 8 if (major, minor) >= (3, 8) else (7 if minor == 7 else 3)
        self._send(b'RFB 003.%03d\n' % minor)
        self.log('server %s, using RFB 3.%d' % (banner.strip().decode('ascii', 'replace'), minor))

        if minor == 3:
            sec = self._u32()
            if sec == 0:
                raise RFBError('server refused: ' + self._reason())
            offered = [sec]
        else:
            n = self._u8()
            if n == 0:
                raise RFBError('server refused: ' + self._reason())
            offered = list(self._recv(n))
        sec = self._choose_security(offered)
        if minor != 3:
            self._send(bytes([sec]))
        self.log('security types offered %s, using %d' % (offered, sec))

        if sec == SEC_VNC:
            if self._password is None:
                raise RFBError('server requires a VNC password (set VNC_PASSWORD_FILE)')
            self._send(vnc_auth_response(self._password, self._recv(16)))
        elif sec == SEC_ARD:
            self._ard_auth()
        if sec != SEC_NONE or minor == 8:
            if self._u32() != 0:
                reason = self._reason() if minor == 8 else 'authentication failed'
                raise RFBError('authentication failed: %s' % reason)
        self._password = None  # not kept after authentication

        self._send(b'\x01')  # ClientInit: shared session
        w, h = struct.unpack('>HH', self._recv(4))
        self._recv(16)  # server pixel format; we impose our own below
        self.name = self._recv(self._u32()).decode('utf-8', 'replace')
        self._resize(w, h)
        # 32bpp little-endian true colour, R at bits 0-7, G 8-15, B 16-23:
        # memory order R,G,B,X and ZRLE CPIXELs are R,G,B.
        self._send(struct.pack('>B3xBBBBHHHBBB3x', 0, 32, 24, 0, 1, 255, 255, 255, 0, 8, 16))
        encs = self.encodings + [ENC_CURSOR, ENC_DESKTOPSIZE, ENC_LASTRECT]
        self._send(struct.pack('>BxH', 2, len(encs)) + b''.join(struct.pack('>i', e) for e in encs))
        self.log('connected to %r %dx%d' % (self.name, w, h))

    def _reason(self):
        return self._recv(self._u32()).decode('utf-8', 'replace')

    def _choose_security(self, offered):
        prefs = [SEC_ARD, SEC_VNC, SEC_NONE] if self._username else [SEC_VNC, SEC_NONE, SEC_ARD]
        for p in prefs:
            if p in offered:
                if p == SEC_ARD and not self._username:
                    raise RFBError('server offers only Apple auth (30); set VNC_USERNAME to the macOS '
                                   'account, or enable "VNC viewers may control screen with password"')
                return p
        raise RFBError('no supported security type in %s' % offered)

    def _ard_auth(self):
        if self._password is None:
            raise RFBError('Apple auth requires a password (set VNC_PASSWORD_FILE)')
        generator = self._u16()
        key_len = self._u16()
        prime = int.from_bytes(self._recv(key_len), 'big')
        server_pub = int.from_bytes(self._recv(key_len), 'big')
        private = int.from_bytes(os.urandom(key_len), 'big') % (prime - 2) + 1
        public = pow(generator, private, prime).to_bytes(key_len, 'big')
        shared = pow(server_pub, private, prime).to_bytes(key_len, 'big')
        creds = bytearray(os.urandom(128))
        user = self._username.encode('utf-8')[:63]
        pw = self._password if isinstance(self._password, bytes) else self._password.encode('utf-8')
        pw = pw[:63]
        creds[0:len(user) + 1] = user + b'\0'
        creds[64:64 + len(pw) + 1] = pw + b'\0'
        self._send(aes128_ecb_encrypt(hashlib.md5(shared).digest(), bytes(creds)) + public)

    # -------------------------------------------------------- reader ----
    def _resize(self, w, h):
        with self._fb_lock:
            self.width, self.height = w, h
            self.fb = bytearray(w * h * 3)

    def _request(self, incremental=True):
        self._last_request = time.monotonic()
        self._send(struct.pack('>BBHHHH', 3, 1 if incremental else 0, 0, 0, self.width, self.height))

    def _read_loop(self):
        try:
            while True:
                kind = self._u8()
                if kind == 0:
                    with self._cond:
                        self.updating = True
                    full = self._framebuffer_update()
                    with self._cond:
                        self.updating = False
                        self.frame_seq += 1
                        self._cond.notify_all()
                    wait = self._last_request + self.min_interval - time.monotonic()
                    if wait > 0:
                        time.sleep(wait)
                    self._request(incremental=not full)
                elif kind == 1:  # SetColourMapEntries (unused in true colour)
                    self._recv(1)
                    self._u16()
                    self._recv(6 * self._u16())
                elif kind == 2:  # Bell
                    pass
                elif kind == 3:  # ServerCutText
                    self._recv(3)
                    n = struct.unpack('>i', self._recv(4))[0]
                    self._recv(abs(n))
                else:
                    raise RFBError('unsupported server message type %d' % kind)
        except Exception as exc:  # connection lost or protocol error
            if self.sock is not None:  # not a deliberate close()
                self.error = str(exc) or exc.__class__.__name__
        finally:
            with self._cond:
                self.closed = True
                self.updating = False
                self._cond.notify_all()
            if self.error:
                self.log('connection ended: %s' % self.error)

    def _framebuffer_update(self):
        """Apply one FramebufferUpdate; returns True if a full refresh is needed."""
        self._recv(1)
        count = self._u16()
        need_full = False
        i = 0
        while count == 0xFFFF or i < count:
            i += 1
            x, y, w, h, enc = struct.unpack('>HHHHi', self._recv(12))
            if enc == ENC_RAW:
                self._blit(x, y, w, h, self._rgbx_to_rgb(self._recv(w * h * 4)))
            elif enc == ENC_COPYRECT:
                sx, sy = struct.unpack('>HH', self._recv(4))
                self._copyrect(sx, sy, x, y, w, h)
            elif enc == ENC_ZLIB:
                data = self._zlib_raw.decompress(self._recv(self._u32()))
                self._blit(x, y, w, h, self._rgbx_to_rgb(data))
            elif enc == ENC_ZRLE:
                data = self._zlib_zrle.decompress(self._recv(self._u32()))
                self._zrle(x, y, w, h, data)
            elif enc == ENC_CURSOR:
                pixels = self._rgbx_to_rgb(self._recv(w * h * 4))
                mask = self._recv(((w + 7) // 8) * h)
                self.cursor = (x, y, w, h, pixels, mask) if w and h else None
            elif enc == ENC_DESKTOPSIZE:
                self._resize(w, h)
                self.log('desktop resized to %dx%d' % (w, h))
                need_full = True
            elif enc == ENC_LASTRECT:
                break
            else:
                raise RFBError('server sent unrequested encoding %d' % enc)
        return need_full

    @staticmethod
    def _rgbx_to_rgb(data):
        n = len(data) // 4
        out = bytearray(n * 3)
        out[0::3] = data[0::4]
        out[1::3] = data[1::4]
        out[2::3] = data[2::4]
        return out

    def _blit(self, x, y, w, h, rgb):
        with self._fb_lock:
            fw, fh = self.width, self.height
            if x >= fw or y >= fh:
                return
            cw = min(w, fw - x)
            stride, src_stride = fw * 3, w * 3
            if x == 0 and cw == fw and w == fw:
                rows = min(h, fh - y)
                self.fb[y * stride:(y + rows) * stride] = rgb[:rows * stride]
                return
            for r in range(min(h, fh - y)):
                d = (y + r) * stride + x * 3
                s = r * src_stride
                self.fb[d:d + cw * 3] = rgb[s:s + cw * 3]

    def _copyrect(self, sx, sy, x, y, w, h):
        with self._fb_lock:
            stride = self.width * 3
            rows = [bytes(self.fb[(sy + r) * stride + sx * 3:(sy + r) * stride + (sx + w) * 3])
                    for r in range(h)]
        self._blit(x, y, w, h, b''.join(rows))

    def _zrle(self, rx, ry, rw, rh, data):
        p = 0
        for ty in range(ry, ry + rh, 64):
            th = min(64, ry + rh - ty)
            for tx in range(rx, rx + rw, 64):
                tw = min(64, rx + rw - tx)
                sub = data[p]
                p += 1
                npix = tw * th
                if sub == 0:
                    tile = data[p:p + npix * 3]
                    p += npix * 3
                elif sub == 1:
                    tile = data[p:p + 3] * npix
                    p += 3
                elif 2 <= sub <= 16:
                    pal = [data[p + 3 * k:p + 3 * k + 3] for k in range(sub)]
                    p += 3 * sub
                    bits = 1 if sub == 2 else (2 if sub <= 4 else 4)
                    mask = (1 << bits) - 1
                    row_bytes = (tw * bits + 7) // 8
                    out = []
                    for _ in range(th):
                        row = data[p:p + row_bytes]
                        p += row_bytes
                        idx = []
                        for byte in row:
                            for shift in range(8 - bits, -1, -bits):
                                idx.append((byte >> shift) & mask)
                        out.extend(pal[k] for k in idx[:tw])
                    tile = b''.join(out)
                elif sub == 128:
                    out, filled = [], 0
                    while filled < npix:
                        px = data[p:p + 3]
                        p += 3
                        run = 1
                        while True:
                            b = data[p]
                            p += 1
                            run += b
                            if b != 255:
                                break
                        out.append(px * run)
                        filled += run
                    tile = b''.join(out)
                elif sub >= 130:
                    n = sub - 128
                    pal = [data[p + 3 * k:p + 3 * k + 3] for k in range(n)]
                    p += 3 * n
                    out, filled = [], 0
                    while filled < npix:
                        k = data[p]
                        p += 1
                        run = 1
                        if k & 0x80:
                            k &= 0x7F
                            while True:
                                b = data[p]
                                p += 1
                                run += b
                                if b != 255:
                                    break
                        out.append(pal[k] * run)
                        filled += run
                    tile = b''.join(out)
                else:
                    raise RFBError('invalid ZRLE subencoding %d' % sub)
                self._blit(tx, ty, tw, th, tile)

    # ------------------------------------------------------- frames -----
    def wait_frame(self, after_seq, timeout):
        """Wait until frame_seq > after_seq; False on timeout/close."""
        deadline = time.monotonic() + timeout
        with self._cond:
            while self.frame_seq <= after_seq and not self.closed:
                left = deadline - time.monotonic()
                if left <= 0:
                    return False
                self._cond.wait(left)
            return self.frame_seq > after_seq

    def wait_idle(self, timeout):
        """Wait for an in-flight framebuffer update to finish applying."""
        deadline = time.monotonic() + timeout
        with self._cond:
            while self.updating and not self.closed:
                left = deadline - time.monotonic()
                if left <= 0:
                    return False
                self._cond.wait(left)
            return True

    def snapshot(self, draw_cursor=True):
        """(width, height, rgb bytearray copy), cursor composited at our pointer."""
        with self._fb_lock:
            w, h, rgb = self.width, self.height, bytearray(self.fb)
        cur, pos = self.cursor, self.pointer_pos
        if draw_cursor and cur and pos:
            hx, hy, cw, ch, pix, mask = cur
            ox, oy = pos[0] - hx, pos[1] - hy
            mrow = (cw + 7) // 8
            for r in range(ch):
                yy = oy + r
                if not 0 <= yy < h:
                    continue
                for c in range(cw):
                    xx = ox + c
                    if 0 <= xx < w and mask[r * mrow + c // 8] & (0x80 >> (c % 8)):
                        d, s = (yy * w + xx) * 3, (r * cw + c) * 3
                        rgb[d:d + 3] = pix[s:s + 3]
        return w, h, rgb

    # -------------------------------------------------------- input -----
    def pointer(self, x, y, buttons=None):
        if buttons is not None:
            self.buttons = buttons
        x = max(0, min(self.width - 1, int(round(x))))
        y = max(0, min(self.height - 1, int(round(y))))
        self.pointer_pos = (x, y)
        self._send(struct.pack('>BBHH', 5, self.buttons, x, y))

    def key(self, keysym, down):
        self._send(struct.pack('>BBxxI', 4, 1 if down else 0, keysym))

    def close(self):
        sock, self.sock = self.sock, None
        self.closed = True
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
