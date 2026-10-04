<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-pkgbuild

The Bazel packaging actions of paperkit's `tools/`, ported here (mtools:W542, paperkit:W142). They
are the layout pathfinder for the rest of that migration. Behaviour is paperkit's; the entry points
are console scripts and `python -m` modules instead of paths.

| module | script | does |
|---|---|---|
| `mikemol.pkgbuild.wheel` | `mikemol-wheel` | `build <out.whl> <pyproject.toml>` builds a wheel through the declared setuptools backend; `install <venv> <wheel> [dep ...]` installs it into a private venv by extraction (stdlib only) |
| `mikemol.pkgbuild.pyc` | `mikemol-pyc` | `<src.py> <out.pyc>` compiles with PEP 552 UNCHECKED_HASH invalidation |
| `mikemol.pkgbuild.pyinfo` | `mikemol-pyinfo` | prints `sys.executable` and the version |

## The `-P` caveat for `wheel build`

paperkit ran `python3 -P tools/wheel.py build ...` because Python puts a script's own directory on
`sys.path`, so `tools/` shadowed the real `wheel` distribution that setuptools imports. Run as
`python -m mikemol.pkgbuild.wheel` or as the console script, the package directory is not on
`sys.path` (the module is addressed as `mikemol.pkgbuild.wheel`), so that shadow cannot arise.
Running the file by path, `python .../pkgbuild/wheel.py`, still reproduces it: keep `-P` there.
