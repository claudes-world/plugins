"""xdotool-style key names -> X11 keysyms, plus text -> key-event plans."""
import os

_NAMED = {
    'return': 0xFF0D, 'enter': 0xFF0D, 'kp_enter': 0xFF8D,
    'tab': 0xFF09, 'iso_left_tab': 0xFE20,
    'escape': 0xFF1B, 'esc': 0xFF1B,
    'backspace': 0xFF08, 'delete': 0xFFFF, 'del': 0xFFFF, 'insert': 0xFF63,
    'home': 0xFF50, 'end': 0xFF57,
    'page_up': 0xFF55, 'pageup': 0xFF55, 'prior': 0xFF55,
    'page_down': 0xFF56, 'pagedown': 0xFF56, 'next': 0xFF56,
    'left': 0xFF51, 'up': 0xFF52, 'right': 0xFF53, 'down': 0xFF54,
    'space': 0x0020, 'spc': 0x0020,
    'caps_lock': 0xFFE5, 'menu': 0xFF67, 'print': 0xFF61,
    'shift': 0xFFE1, 'shift_l': 0xFFE1, 'shift_r': 0xFFE2,
    'ctrl': 0xFFE3, 'control': 0xFFE3, 'control_l': 0xFFE3, 'control_r': 0xFFE4,
    'alt': 0xFFE9, 'alt_l': 0xFFE9, 'alt_r': 0xFFEA, 'option': 0xFFE9, 'opt': 0xFFE9,
    'meta_l': 0xFFE7, 'meta_r': 0xFFE8, 'super_l': 0xFFEB, 'super_r': 0xFFEC,
    'minus': 0x2D, 'plus': 0x2B, 'equal': 0x3D, 'comma': 0x2C, 'period': 0x2E,
    'slash': 0x2F, 'backslash': 0x5C, 'semicolon': 0x3B, 'apostrophe': 0x27,
    'grave': 0x60, 'bracketleft': 0x5B, 'bracketright': 0x5D,
    'volume_up': 0x1008FF13, 'volume_down': 0x1008FF11, 'mute': 0x1008FF12,
}
for _i in range(1, 25):
    _NAMED['f%d' % _i] = 0xFFBE + _i - 1

# Command key: Apple's Screen Sharing maps Super to Command. Override with
# VNC_CMD_KEYSYM=Meta_L (or a hex keysym) if a server maps it differently.
_CMD_ALIASES = ('cmd', 'command', 'super', 'meta', 'win', 'windows')

# US-layout characters that need Shift held.
SHIFTED = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ~!@#$%^&*()_+{}|:"<>?')
SHIFT = 0xFFE1


def cmd_keysym():
    raw = os.environ.get('VNC_CMD_KEYSYM', 'Super_L').strip()
    if raw.lower().startswith('0x'):
        return int(raw, 16)
    return _NAMED.get(raw.lower(), 0xFFEB)


def char_keysym(ch):
    if ch == '\n':
        return 0xFF0D
    if ch == '\t':
        return 0xFF09
    if ch == '\b':
        return 0xFF08
    cp = ord(ch)
    if 0x20 <= cp <= 0x7E or 0xA0 <= cp <= 0xFF:
        return cp
    return 0x01000000 | cp  # X11 Unicode keysym


def name_keysym(name):
    low = name.lower()
    if low in _CMD_ALIASES:
        return cmd_keysym()
    if low in _NAMED:
        return _NAMED[low]
    if low.startswith('0x'):
        return int(low, 16)
    if len(name) == 1:
        return char_keysym(name)
    raise ValueError('unknown key name: %r' % name)


def parse_combo(combo):
    """'cmd+shift+t' -> [keysyms] pressed in order, released in reverse.
    A literal '+' key can be written 'plus' (or as the final token: 'ctrl++')."""
    combo = combo.strip()
    if not combo:
        raise ValueError('empty key combo')
    if combo == '+':
        return [0x2B]
    parts = combo.split('+')
    if combo.endswith('++'):
        parts = parts[:-2] + ['plus']
    names = [p for p in parts if p != '']
    syms = [name_keysym(p) for p in names]
    # Single shifted character like 'A' or '?' -> add Shift so every server
    # produces the shifted glyph regardless of its keysym handling.
    if len(names) == 1 and len(names[0]) == 1 and names[0] in SHIFTED:
        syms = [SHIFT] + syms
    return syms


def parse_sequence(keys):
    """xdotool-style: space-separated combos, e.g. 'ctrl+a Delete'."""
    return [parse_combo(tok) for tok in keys.split()] if keys.strip() != '+' else [[0x2B]]


def text_plan(text):
    """Yield (keysyms_to_hold, keysym) per character of text."""
    for ch in text:
        if ch == '\r':
            continue
        sym = char_keysym(ch)
        yield ([SHIFT] if ch in SHIFTED else []), sym
