"""Non-leak canaries and mutation tests for the new source repository boundary."""
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

from check_public import validate, snapshot


def fixture():
    files = {'.claude-plugin/marketplace.json': json.dumps({'name':'claudes-world-core', 'plugins':[{'name':'ready','source':'./plugins/ready'}]}).encode(),
             'plugins/ready/.claude-plugin/plugin.json': b'{"name":"ready","version":"1.0.0"}',
             'plugins/ready/bin/run': b'#!/bin/sh\necho public\n',
             'plugins/ready/.hidden-asset': b'public fixture',
             'plugins/internal/.hidden-asset': b'EXCLUDED_PRIVATE_CANARY',
             'plugins/paid/bin/run': b'EXCLUDED_PREMIUM_CANARY',
             'plugins/unclassified/data': b'EXCLUDED_UNKNOWN_CANARY',
             'internal-notes.md': b'EXCLUDED_METADATA_CANARY'}
    return files


def select(files):
    return {path:data for path,data in files.items() if path == '.claude-plugin/marketplace.json' or path.startswith('plugins/ready/')}


class PublicBoundaryTests(unittest.TestCase):
    def test_exact_closure_archive_and_canaries(self):
        files=select(fixture())
        self.assertEqual(set(files), {'.claude-plugin/marketplace.json','plugins/ready/.claude-plugin/plugin.json','plugins/ready/bin/run','plugins/ready/.hidden-asset'})
        self.assertEqual(validate(files,allowed={'ready'}), [])
        buffer=io.BytesIO()
        with tarfile.open(fileobj=buffer,mode='w') as archive:
            for name,data in sorted(files.items()):
                info=tarfile.TarInfo(name);info.size=len(data);archive.addfile(info,io.BytesIO(data))
        self.assertNotIn(b'EXCLUDED_',buffer.getvalue())
        buffer.seek(0)
        with tarfile.open(fileobj=buffer) as archive:
            self.assertEqual(set(archive.getnames()),set(files))

    def test_determinism_private_independence_core_sensitivity(self):
        source=fixture(); original=select(source)
        self.assertEqual(original,select(source))
        source['plugins/internal/.hidden-asset']=b'changed';self.assertEqual(original,select(source))
        source['plugins/ready/bin/run']=b'changed';self.assertNotEqual(original,select(source))

    def test_aggregate_mutation_fails_exclusion_assertions(self):
        self.assertTrue(validate(fixture(),allowed={'ready'}))
        self.assertIn(b'EXCLUDED_',b'\n'.join(fixture().values()))

    def test_cross_boundary_import_asset_and_membership_withhold_candidate(self):
        prior=select(fixture())
        for reference in (b"import '../../internal/module'",b'[asset](../../paid/image.png)'):
            candidate=dict(prior);candidate['plugins/ready/bin/run']=reference
            self.assertTrue(validate(candidate,allowed={'ready'}))
            self.assertEqual(prior,select(fixture()))
        candidate=dict(prior)
        candidate['.claude-plugin/marketplace.json']=b'{"name":"claudes-world-core","plugins":[{"name":"paid","source":"./plugins/paid"}]}'
        self.assertTrue(validate(candidate,allowed={'ready'}))

    def test_escaping_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);subprocess.run(['git','init','-q',str(root)],check=True)
            (root/'asset').symlink_to('../private-asset')
            subprocess.run(['git','-C',str(root),'add','asset'],check=True)
            with self.assertRaisesRegex(ValueError,'symlink'):
                snapshot(root)

    def test_isolated_fixture_entrypoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);script=root/'run';script.write_bytes(select(fixture())['plugins/ready/bin/run']);script.chmod(0o755)
            result=subprocess.run([str(script)],cwd=root,env={'PATH':'/usr/bin:/bin','HOME':str(root)},capture_output=True,check=True)
            self.assertEqual(result.stdout,b'public\n')


if __name__ == '__main__':
    unittest.main()
