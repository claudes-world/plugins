#!/usr/bin/env python3
"""Rig-free unit tests: crypto vectors, key parsing, PNG, ZRLE, config safety.

Run: python3 test/test_unit.py   (stdlib only)
"""
import os
import struct
import sys
import unittest
import zlib

sys.path[:0] = [os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]  # plugin root for imports

from vnclib import imaging, keys  # noqa: E402
from vnclib.crypto import aes128_ecb_encrypt, des_ecb_encrypt, vnc_auth_response  # noqa: E402
from vnclib.rfb import RFBClient  # noqa: E402
import server  # noqa: E402


class CryptoTests(unittest.TestCase):
    def test_des_fips_vector(self):
        self.assertEqual(des_ecb_encrypt(bytes.fromhex('133457799BBCDFF1'),
                                         bytes.fromhex('0123456789ABCDEF')).hex(), '85e813540f0ab405')

    def test_aes_fips197_vector(self):
        self.assertEqual(aes128_ecb_encrypt(bytes(range(16)), bytes.fromhex('00112233445566778899aabbccddeeff')).hex(),
                         '69c4e0d86a7b0430d8cdb78070b4c55a')

    def test_vnc_auth_uses_bit_reversed_key(self):
        # key byte 0x01 reversed is 0x80; DES ignores parity bits, so 0x80 == 0x81.
        self.assertEqual(vnc_auth_response(b'\x01' * 8, bytes(16)),
                         des_ecb_encrypt(b'\x80' * 8, bytes(16)))
        self.assertEqual(len(vnc_auth_response('longpassword', bytes(16))), 16)


class KeyTests(unittest.TestCase):
    def test_combos(self):
        self.assertEqual(keys.parse_combo('ctrl+c'), [0xFFE3, ord('c')])
        self.assertEqual(keys.parse_combo('Return'), [0xFF0D])
        self.assertEqual(keys.parse_combo('cmd+l'), [0xFFEB, ord('l')])
        self.assertEqual(keys.parse_combo('shift+Tab'), [0xFFE1, 0xFF09])
        self.assertEqual(keys.parse_combo('ctrl++'), [0xFFE3, 0x2B])
        self.assertEqual(keys.parse_combo('F5'), [0xFFC2])
        self.assertEqual(keys.parse_combo('?'), [0xFFE1, ord('?')])
        self.assertEqual(keys.parse_sequence('ctrl+a Delete'), [[0xFFE3, ord('a')], [0xFFFF]])
        with self.assertRaises(ValueError):
            keys.parse_combo('nosuchkey')

    def test_cmd_override(self):
        os.environ['VNC_CMD_KEYSYM'] = 'Meta_L'
        try:
            self.assertEqual(keys.parse_combo('cmd+l')[0], 0xFFE7)
        finally:
            del os.environ['VNC_CMD_KEYSYM']

    def test_text_plan_shift_and_unicode(self):
        plan = list(keys.text_plan('aA:\né☃'))
        self.assertEqual(plan[0], ([], ord('a')))
        self.assertEqual(plan[1], ([keys.SHIFT], ord('A')))
        self.assertEqual(plan[2], ([keys.SHIFT], ord(':')))
        self.assertEqual(plan[3], ([], 0xFF0D))
        self.assertEqual(plan[4], ([], 0xE9))
        self.assertEqual(plan[5], ([], 0x01002603))


class ImagingTests(unittest.TestCase):
    def test_default_scale(self):
        self.assertEqual(imaging.default_scale(1280, 800), 1.0)
        self.assertAlmostEqual(imaging.default_scale(1920, 1080), 1568 / 1920)
        self.assertEqual(imaging.scaled_size(1920, 1080, 1568 / 1920), (1568, 882))
        self.assertEqual(imaging.default_scale(1920, 1080, '0.5'), 0.5)
        with self.assertRaises(ValueError):
            imaging.default_scale(10, 10, '1.5')

    def test_stdlib_png_and_nearest_scale(self):
        rgb = bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255])  # 2x2
        png = imaging._png_stdlib(rgb, 2, 2, 6)
        self.assertTrue(png.startswith(b'\x89PNG\r\n\x1a\n'))
        idat = png[png.index(b'IDAT') + 4:png.index(b'IEND') - 8]
        self.assertEqual(zlib.decompress(idat), b'\x00' + rgb[:6] + b'\x00' + rgb[6:])
        self.assertEqual(imaging._scale_nearest(rgb, 2, 2, 1, 1), rgb[9:12])

    def test_crop_clamps(self):
        rgb = bytes(range(4 * 4 * 3))
        part, w, h = imaging.crop(rgb, 4, 4, 2, 2, 10, 10)
        self.assertEqual((w, h), (2, 2))
        self.assertEqual(part[:3], rgb[(2 * 4 + 2) * 3:(2 * 4 + 2) * 3 + 3])


class ZRLETests(unittest.TestCase):
    def client(self, w, h):
        c = RFBClient('127.0.0.1')
        c._resize(w, h)
        return c

    def test_subencodings(self):
        red, blue, white = b'\xff\x00\x00', b'\x00\x00\xff', b'\xff\xff\xff'
        c = self.client(4, 2)
        # solid tile
        c._zrle(0, 0, 4, 2, b'\x01' + red)
        self.assertEqual(bytes(c.fb), red * 8)
        # raw tile
        raw = bytes(range(24))
        c._zrle(0, 0, 4, 2, b'\x00' + raw)
        self.assertEqual(bytes(c.fb), raw)
        # packed palette (2 colours, 1 bit/px, rows byte-padded): 1010 / 0101
        c._zrle(0, 0, 4, 2, bytes([2]) + red + blue + bytes([0b10100000, 0b01010000]))
        self.assertEqual(bytes(c.fb), blue + red + blue + red + red + blue + red + blue)
        # plain RLE: 3x white, 5x red
        c._zrle(0, 0, 4, 2, b'\x80' + white + b'\x02' + red + b'\x04')
        self.assertEqual(bytes(c.fb), white * 3 + red * 5)
        # palette RLE (2 colours): idx0 run 6, idx1 single, idx1 single
        c._zrle(0, 0, 4, 2, bytes([130]) + red + blue + bytes([0x80, 5, 1, 1]))
        self.assertEqual(bytes(c.fb), red * 6 + blue * 2)

    def test_multi_tile_and_offset_blit(self):
        c = self.client(70, 2)
        green = b'\x00\xff\x00'
        c._zrle(0, 0, 70, 2, b'\x01' + green + b'\x01' + b'\x01\x02\x03')  # 64-wide tile + 6-wide tile
        self.assertEqual(bytes(c.fb[0:3]), green)
        self.assertEqual(bytes(c.fb[64 * 3:65 * 3]), b'\x01\x02\x03')
        self.assertEqual(bytes(c.fb[(70 + 69) * 3:]), b'\x01\x02\x03')

    def test_rgbx_and_copyrect(self):
        c = self.client(2, 2)
        c._blit(0, 0, 2, 2, RFBClient._rgbx_to_rgb(struct.pack('16B', *range(16))))
        self.assertEqual(bytes(c.fb[:6]), bytes([0, 1, 2, 4, 5, 6]))
        c._copyrect(0, 0, 1, 1, 1, 1)
        self.assertEqual(bytes(c.fb[9:12]), bytes([0, 1, 2]))


class ConfigSafetyTests(unittest.TestCase):
    def test_requires_host(self):
        with self.assertRaises(server.ToolError):
            server.Config({}).check()

    def test_allowlist(self):
        server.Config({'VNC_HOST': '127.0.0.1'}).check()
        with self.assertRaises(server.ToolError):
            server.Config({'VNC_HOST': '192.0.2.10'}).check()
        server.Config({'VNC_HOST': '192.0.2.10', 'VNC_ALLOW_HOSTS': '192.0.2.10'}).check()

    def test_password_file_only(self):
        cfg = server.Config({'VNC_HOST': '127.0.0.1', 'VNC_PASSWORD': 'x'})
        self.assertIsNone(cfg.read_password())  # VNC_PASSWORD is deliberately ignored

    def test_tools_list_and_unknown_method(self):
        srv = server.Server(server.Session(server.Config({})))
        tools = srv.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'})['result']['tools']
        self.assertIn('record_start', [t['name'] for t in tools])
        self.assertEqual(srv.handle({'jsonrpc': '2.0', 'id': 2, 'method': 'nope'})['error']['code'], -32601)
        res = srv.handle({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
                          'params': {'name': 'screenshot', 'arguments': {}}})['result']
        self.assertTrue(res['isError'])
        self.assertIn('VNC_HOST is not set', res['content'][0]['text'])


if __name__ == '__main__':
    unittest.main()
