#!/usr/bin/env python3
"""Regression tests for the local background-removal CLI."""

from __future__ import annotations

import base64
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw


PLUGIN = Path(__file__).resolve().parents[1]
SCRIPT = PLUGIN / "skills/image-assets/scripts/bg-remove"
FIXTURES = PLUGIN / "test/fixtures"


def load_bg_remove():
    loader = importlib.machinery.SourceFileLoader("image_assets_bg_remove", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


BG_REMOVE = load_bg_remove()


def decode_fixture(name: str, destination: Path) -> Path:
    encoded = (FIXTURES / f"{name}.base64").read_text().strip()
    destination.write_bytes(base64.b64decode(encoded))
    return destination


class BackgroundRemovalTests(unittest.TestCase):
    def test_stray_alpha_is_not_meaningful(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = decode_fixture("stray-alpha.png", Path(directory) / "stray.png")
            with Image.open(source) as image:
                self.assertFalse(BG_REMOVE.has_real_transparency(image.convert("RGBA")))

    def test_explicit_engine_forces_processing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = decode_fixture("already-transparent.png", root / "source.png")
            output = root / "output.png"
            result = subprocess.run(
                [SCRIPT, source, "-o", output, "--engine", "border"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("via border", result.stdout)

    def test_halo_clean_preserves_three_pixel_outline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = decode_fixture("outlined-halo.png", Path(directory) / "outline.png")
            with Image.open(source) as opened:
                original = opened.convert("RGBA")

            for radius, expected_light_pixels in ((1, 35), (2, 0)):
                with self.subTest(radius=radius):
                    cleaned = BG_REMOVE.clean_halo(original, radius)
                    visible = [pixel for pixel in cleaned.getdata() if pixel[3] > 0]
                    dark_outline = sum(max(pixel[:3]) < 32 for pixel in visible)
                    light_fringe = sum(min(pixel[:3]) > 240 for pixel in visible)
                    self.assertEqual(dark_outline, 180)
                    self.assertEqual(light_fringe, expected_light_pixels)

    def test_alpha_verification_is_default_and_loud(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = decode_fixture("checkerboard-opaque.png", root / "source.png")
            output = root / "output.png"
            fake_module = root / "rembg.py"
            fake_module.write_text(
                "def new_session(model): return model\n"
                "def remove(source, **options): return source\n"
            )
            environment = {**os.environ, "PYTHONPATH": str(root)}

            rejected = subprocess.run(
                [SCRIPT, source, "-o", output, "--engine", "rembg"],
                capture_output=True,
                text=True,
                env=environment,
                check=False,
            )
            self.assertEqual(rejected.returncode, 3)
            self.assertIn("ALPHA VERIFICATION FAILED", rejected.stderr)
            self.assertFalse(output.exists())

            allowed = subprocess.run(
                [
                    SCRIPT,
                    source,
                    "-o",
                    output,
                    "--engine",
                    "rembg",
                    "--no-verify-alpha",
                ],
                capture_output=True,
                text=True,
                env=environment,
                check=False,
            )
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            self.assertTrue(output.exists())

    def test_exif_orientation_is_applied_before_processing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "rotated.jpg"
            output = root / "output.png"
            image = Image.new("RGB", (20, 10), "white")
            ImageDraw.Draw(image).rectangle((6, 2, 13, 7), fill=(200, 30, 30))
            exif = image.getexif()
            exif[274] = 6
            image.save(source, exif=exif)

            result = subprocess.run(
                [SCRIPT, source, "-o", output, "--engine", "border"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with Image.open(output) as processed:
                self.assertEqual(processed.size, (10, 20))


if __name__ == "__main__":
    unittest.main()
