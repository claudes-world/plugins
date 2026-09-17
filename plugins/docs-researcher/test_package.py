"""Run from this directory with python3 test_package.py; no repository required."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent
ENTRIES = ['agents/docs-researcher.md']

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
    def test_pinned_context7_tools_and_unavailable_fallback(self):
        agent = ROOT.joinpath('agents/docs-researcher.md').read_text()
        self.assertIn('mcp__plugin_docs-researcher_context7__query-docs', agent)
        self.assertIn('`libraryId`', agent)
        self.assertIn('`query`', agent)
        self.assertIn('Context7 MCP unavailable', agent)
        self.assertIn('falling back to web sources, doc-version fidelity reduced.', agent)
        mcp = json.loads(ROOT.joinpath('.mcp.json').read_text())['mcpServers']['context7']
        self.assertEqual(mcp['args'], ['-y', '@upstash/context7-mcp@3.2.3'])

    def test_provider_requirements_and_license_are_local(self):
        self.assertEqual(json.loads(ROOT.joinpath('providers.json').read_text())['required_paid_services'], [])
        self.assertIn('MIT License', ROOT.joinpath('LICENSE').read_text())
        self.assertTrue(ROOT.joinpath('THIRD_PARTY_NOTICES.md').read_text())

if __name__ == '__main__':
    unittest.main()
