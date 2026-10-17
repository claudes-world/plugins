"""RGB framebuffer -> PNG, with optional downscale/crop.

Uses Pillow when importable (fast, smooth resampling); otherwise falls back to
a stdlib-only PNG writer and nearest-neighbour scaling.
"""
import struct
import zlib

try:  # optional accelerator
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover - exercised on hosts without Pillow
    Image = None

MAX_LONG_EDGE = 1568


def have_pillow():
    return Image is not None


def default_scale(width, height, override=None):
    if override:
        s = float(override)
        if not 0 < s <= 1:
            raise ValueError('VNC_SCALE must be in (0, 1]')
        return s
    long_edge = max(width, height)
    return 1.0 if long_edge <= MAX_LONG_EDGE else MAX_LONG_EDGE / long_edge


def scaled_size(width, height, scale):
    return max(1, round(width * scale)), max(1, round(height * scale))


def _png_chunk(kind, data):
    return (struct.pack('>I', len(data)) + kind + data
            + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF))


def _png_stdlib(rgb, width, height, level):
    stride = width * 3
    raw = b''.join(b'\x00' + bytes(rgb[y * stride:(y + 1) * stride]) for y in range(height))
    return (b'\x89PNG\r\n\x1a\n'
            + _png_chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + _png_chunk(b'IDAT', zlib.compress(raw, level))
            + _png_chunk(b'IEND', b''))


def crop(rgb, width, height, x, y, w, h):
    x = max(0, min(width - 1, int(x)))
    y = max(0, min(height - 1, int(y)))
    w = max(1, min(width - x, int(w)))
    h = max(1, min(height - y, int(h)))
    stride = width * 3
    out = b''.join(bytes(rgb[(y + r) * stride + x * 3:(y + r) * stride + (x + w) * 3]) for r in range(h))
    return out, w, h


def _scale_nearest(rgb, width, height, out_w, out_h):
    stride = width * 3
    cols = [min(width - 1, int((c + 0.5) * width / out_w)) * 3 for c in range(out_w)]
    rows = []
    for r in range(out_h):
        sy = min(height - 1, int((r + 0.5) * height / out_h))
        row = rgb[sy * stride:(sy + 1) * stride]
        rows.append(b''.join(row[c:c + 3] for c in cols))
    return b''.join(rows)


def encode_png(rgb, width, height, out_size=None, level=6):
    """Encode an RGB buffer; out_size=(w, h) resamples first."""
    if out_size and out_size != (width, height):
        if Image is not None:
            img = Image.frombytes('RGB', (width, height), bytes(rgb))
            img = img.resize(out_size, Image.LANCZOS)
        else:
            rgb = _scale_nearest(rgb, width, height, *out_size)
            width, height = out_size
            img = None
    elif Image is not None:
        img = Image.frombytes('RGB', (width, height), bytes(rgb))
    else:
        img = None
    if img is not None:
        import io
        buf = io.BytesIO()
        img.save(buf, 'PNG', compress_level=level)
        return buf.getvalue()
    return _png_stdlib(rgb, width, height, level)
