"""Run from this directory with python3 test_package.py; no repository required."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent
ENTRIES = ['skills/bakeoff/SKILL.md', 'skills/grill-me/SKILL.md', 'skills/mechanic/SKILL.md', 'skills/researcher/SKILL.md', 'skills/wingman/SKILL.md']

class InstalledContentTests(unittest.TestCase):
    def test_discoverable_entrypoints_and_local_references(self):
        manifest = json.loads((ROOT / '.claude-plugin/plugin.json').read_text())
        self.assertTrue(manifest['name'])
        self.assertEqual(manifest['license'], 'MIT')
        for entry in ENTRIES:
            with self.subTest(entry=entry):
                text = ROOT.joinpath(entry).read_text()
                self.assertTrue(text.startswith('---\n'))
                frontmatter = text.split('---', 2)[1]
                self.assertRegex(frontmatter, r'(?m)^name: .+')
                self.assertRegex(frontmatter, r'(?m)^description: .+')
                self.assertNotRegex(text, r'/home/|\.\./')
                for ref in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
                    if '://' not in ref and not ref.startswith('#'):
                        self.assertTrue((ROOT / entry).parent.joinpath(ref.split('#')[0]).exists(), ref)
    def test_provider_requirements_and_license_are_local(self):
        self.assertEqual(json.loads(ROOT.joinpath('providers.json').read_text())['required_paid_services'], [])
        self.assertIn('MIT License', ROOT.joinpath('LICENSE').read_text())
        self.assertTrue(ROOT.joinpath('THIRD_PARTY_NOTICES.md').read_text())

if __name__ == '__main__':
    unittest.main()
