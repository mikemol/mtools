<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-mdstruct

This package reads and writes markdown by its structure, working over pandoc's AST. It reports
header spans, section sizes, list items, tables and cells, and it rewrites a named section. It
never works line by line on the text. It has one console script, `mdstruct`, with one mode per
structural question. Every mode prints its denominator, so *no matches* and *nothing read* look
different.

```console
$ mdstruct spans tiny.md
  L   1-14     # Title
  L   5-10       ## Alpha
  L  11-14       ## Beta
  3 section(s) in tiny.md

$ mdstruct rows tiny.md
  table 0  1 | 2
  1 row(s) in tiny.md

$ mdstruct lint tiny.md
  tiny.md: no shape findings
```

These runs are real, against a 14-line scratch file with two sections and one 2-column table.
The paths have been shortened.

## Modes

- **Read modes:** `spans`, `budget`, `items`, `grep`, `tables`, `rows`, `classify`, `labels`.
- **Normalization modes:** `roundtrip`, `fixpoint`.
- **Shape modes:** `lint [--width N]`, `verify`, `narrowest`.
- **Write modes:** `replace-section HEADING FILE.md --body-file B.md` and `append-section`. Both are
  a dry run unless you pass `--apply`. The body is always a file (`-` means stdin), never an
  argument (`cli.py`).

Run `mdstruct --help` for the full synopsis.

## Adopting

Install from git by subdirectory, pinned to a sha. See the repo-root [INSTALL.md](../INSTALL.md):

```toml
"mikemol-mdstruct @ git+https://github.com/mikemol/mtools.git@<sha>#subdirectory=mdstruct"
```

**`pandoc` must be on PATH.** It is a system binary, not a wheel, so it cannot be declared as a
dependency. If pandoc is missing, this package raises an error; it does not return an empty
string. The test suites report a declared skip for it (`pandoc.py`). The only Python dependency is
`panflute`.

## Why it is built this way

- **A console script, not a symlink.** Peers used to adopt this tool by symlinking one file out of
  another repo's checkout. The tool worked out its root with `abspath(__file__)`, which does not
  resolve the link, so the root became the consumer's repo (`cli.py`, `pyproject.toml`).
- **Pandoc runs in one module only.** Running it is one responsibility, and the exemption a
  subprocess needs is granted per file. The document goes to pandoc on stdin and never becomes a
  word in the command (`pandoc.py`).
- **Frontmatter is re-attached only for a markdown writer.** ⚑ Re-attaching it every time broke
  every AST mode on every `---`-fenced document, for the whole life of the original tool. A
  consumer diagnosed the bug and chose not to patch their symlinked copy, because a local patch
  would have forked the code silently (`pandoc.py`).
- **Lint measures rules instead of turning them off.** `lint` exists because four markdownlint
  rules were about to be disabled before anyone had measured them. ⚑ Code spans are masked before
  any check runs. An earlier proximity heuristic produced a false positive, and printing the
  source line caught it before anyone edited prose that was already correct (`lint.py`).
  - Known limit: `lint` excludes fenced code blocks but not indented ones.
- **Warning filters live in `__init__`.** A `SyntaxWarning` raised while panflute compiles is
  filtered by its message. ⚑ On a developer host it never showed, because panflute's
  `__pycache__` meant nothing recompiled. In a hermetic sandbox it reached stderr on every run
  (`pyproject.toml`).
- **A namespace distribution.** `mdstruct` on PyPI is an unrelated header splitter. The
  `mikemol.` prefix is a PEP 420 namespace with no `__init__.py`, so sibling distributions install
  side by side (`pyproject.toml`).

## Used by the mtools gate

For each staged `.md` file, `.githooks/pre-commit` runs `mdstruct verify`, which refuses a heading
that a bounded write could not reach. It also runs `mdstruct lint` and refuses the commit if the
count of ragged table rows (MD056) grows against `HEAD`.

Requirements: Python ≥ 3.13, `panflute`, and `pandoc` on PATH.
