# Plugins

Source of truth for six public core plugins: docs-researcher, image-gen,
interaction-craft, mindsets, operators, and wingman. Contributions and fixes
belong in this repository.

The root Claude marketplace is `claudes-world-core`. Each directory under
`plugins/` is also an independent installation root. Read its README for setup,
optional provider requirements, and local tests. Operators and Wingman include
ready-to-run bundles; their source and locked build dependencies are included.

Owned code and content are MIT licensed. Preserve each package's full
THIRD_PARTY_NOTICES.md; third-party material retains its original terms.

Before pushing, run `python3 -m unittest discover -s tests -v` and
`python3 tests/check_public.py .`, then the changed package's tests.
