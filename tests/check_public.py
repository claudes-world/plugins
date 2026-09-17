#!/usr/bin/env python3
"""Check the committed public tree before pushing; diagnostics never echo values."""
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

CORE = frozenset({'docs-researcher', 'image-gen', 'interaction-craft', 'mindsets', 'operators', 'wingman'})
METADATA = frozenset({'README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', '.gitignore',
                     '.claude-plugin/marketplace.json', 'tests/check_public.py',
                     'tests/test_public_boundary.py', '.github/workflows/public-boundary.yml'})
PRIVATE_REFERENCES = tuple(s.encode() for s in (
    'claude' + '.do', 'chain' + 'tail', '/srv/' + 'world', 'do' + '-box',
    '/home/' + 'claude', '.se' + 'crets/', 'world' + '-os',
))
EMAIL = re.compile(rb'[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
TOKEN = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9_-]{32,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)')
RELATIVE_REFERENCE = re.compile(rb'''["'(`\s]((?:\.\./)+[^\s"'`)]+)''')


def validate(files, *, allowed=CORE):
    errors = []
    for name, data in sorted(files.items()):
        parts = PurePosixPath(name).parts
        if name not in METADATA and not (len(parts) >= 3 and parts[0] == 'plugins' and parts[1] in allowed):
            errors.append((name, 'outside public path set'))
        if any(part in {'.git', '.env', '.secrets', 'node_modules'} for part in parts):
            errors.append((name, 'excluded asset'))
        if any(marker.lower() in data.lower() for marker in PRIVATE_REFERENCES):
            errors.append((name, 'private reference'))
        if TOKEN.search(data):
            errors.append((name, 'credential signature'))
        # License author credits must remain verbatim. They are reviewed attribution.
        if EMAIL.search(data) and not name.endswith(('THIRD_PARTY_NOTICES.md', 'LICENSE')):
            errors.append((name, 'email outside attribution'))
        if parts[:1] == ('plugins',):
            for match in RELATIVE_REFERENCE.finditer(data):
                path = list(parts[:-1])
                for part in match.group(1).decode(errors='replace').split('/'):
                    if part == '..':
                        if path: path.pop()
                    elif part != '.': path.append(part)
                if path[:2] != list(parts[:2]):
                    errors.append((name, 'reference escapes plugin'))
                    break
    try:
        manifest = json.loads(files['.claude-plugin/marketplace.json'])
        if manifest['name'] != 'claudes-world-core':
            errors.append(('.claude-plugin/marketplace.json', 'catalog identity'))
        names = []
        for entry in manifest['plugins']:
            name = entry['name']; names.append(name)
            source = entry['source']
            if name not in allowed or source != f'./plugins/{name}':
                errors.append(('.claude-plugin/marketplace.json', 'non-public catalog entry'))
            elif f'plugins/{name}/.claude-plugin/plugin.json' not in files:
                errors.append((source, 'unresolved plugin manifest'))
        roots = {PurePosixPath(p).parts[1] for p in files if p.startswith('plugins/')}
        if roots != set(names) or len(names) != len(set(names)):
            errors.append(('.claude-plugin/marketplace.json', 'catalog/tree mismatch'))
    except (KeyError, ValueError, TypeError):
        errors.append(('.claude-plugin/marketplace.json', 'invalid catalog'))
    return errors


def snapshot(root):
    files = {}
    # Git's index is the push boundary; ignore local caches, never scan credentials.
    names = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z']).decode().split('\0')
    for name in filter(None, names):
        path = root / name
        if path.is_symlink():
            raise ValueError(f'{name}: symlink is not a closed public asset')
        files[name] = path.read_bytes()
    return files


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
    try:
        files = snapshot(root)
        errors = validate(files)
    except (OSError, ValueError) as error:
        print(f'FAIL: {error}')
        return 1
    for path, reason in errors:
        print(f'FAIL: {path}: {reason}')
    if not errors:
        print(f'PASS: {len(files)} tracked files; public path set, catalog closure, private references, credential signatures, email attribution, and relative references checked')
        print(f'Catalog plugins: {len(json.loads(files[".claude-plugin/marketplace.json"])["plugins"])}')
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
