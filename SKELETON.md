# The component skeleton

## First, arm the clone

    ./setup.sh

⚑⚑ **A FRESH CLONE HAS NO GATES AND LOOKS EXACTLY LIKE ONE THAT PASSES THEM.** `core.hooksPath`
is per-clone git config rather than a tracked file, so `.githooks/pre-commit` sits in the tree and
never runs until this is done. Measured: `git config --get core.hooksPath` in a fresh clone
returns nothing.

⚑ **NOTHING ELSE NEEDS INSTALLING TO CHECK YOUR WORK.** `bazel test //...` passes 34 of 34 in a
clone with no venvs at all — every tool it needs is a hash-pinned declared input. The venvs are a
developer convenience for fast iteration, not a precondition.

⚑ **THIS IS A POINTER TO A WORKED EXAMPLE, NOT A SPECIFICATION.** `ratchet/` is the newest
distribution here and was built to this shape from nothing; clone it rather than reading a list and
reconstructing it. A specification is something a contributor must interpret, and every
interpretation is a place two repos diverge.

    cp -r ratchet <name> && rm -rf <name>/.venv <name>/ratchet-preview.txt
    # then: rename src/mikemol/ratchet -> src/mikemol/<name>, and edit the identity fields below

## What must change

| file | what is yours |
|------|---------------|
| `pyproject.toml` | `name`, `description`, `keywords`, `dependencies`, `[project.scripts]`, `per-file-ignores`, `markers` |
| `paper.toml` | `title`, `subtitle`, `out` |
| `rubric.tsv` | your sections |
| `warrants.bib` | your claims, one per test function |
| `src/mikemol/<name>/` | the code |
| `tests/` | one `test_<module>.py` per source module |
| `BUILD.bazel` | the `<name>` in the library target and its `deps` |

## What must NOT change, and why

⚑⚑ **NO `src/mikemol/__init__.py`, EVER.** PEP 420 namespace. An `__init__.py` at that level makes
the first-installed distribution the exclusive owner of the `mikemol` prefix and shadows every
sibling — so `mikemol-hooks` and `mikemol-mdstruct` would stop being co-installable, which is the
whole point of splitting them.

⚑⚑ **THE BAR IS COPIED VERBATIM.** `select = ["ALL"]`, `ignore = ["D203", "D213", "COM812"]` and
nothing else, mypy `strict` with `disallow_any_expr`, `files = ["src", "tests"]`, no
`[[tool.mypy.overrides]]`. **DECLARE, NEVER SUPPRESS**: `INP001` is answered by
`namespace-packages`, not by an ignore. Every deviation is a declaration carrying the measurement
that produced it — never an inherited exemption. A fourth `ignore` entry fails
`hooks/tests/test_bar_fires.py`, deliberately.

⚑⚑ **TWO LOCKS, GENERATED NOT HAND-WRITTEN.**

    uv pip compile pyproject.toml --output-file requirements.txt
    uv pip compile --group dev pyproject.toml --output-file requirements-dev.txt

The shipping lock is what a consumer installs; the dev lock is what a witness runs under. They are
different questions. Merging them ships a test runner to every consumer; omitting the dev lock
leaves a bazel `py_test` with no pytest to run.

⚑ **THE HEADER IS GATED, BOTH LINES, ADJACENT AND IN ORDER.**

    # SPDX-License-Identifier: Apache-2.0
    # Copyright (c) 2026 Mike Mol

A shebang may precede it; nothing may come between the two lines. The pattern is stricter than its
prose — order, adjacency, the `#` prefix and a four-digit year are all fixed — so a file with both
lines in the wrong order fails while looking correct to a reader.

⚑ **EVERY TEST ARRIVES WARRANTED.** `.githooks/pre-commit` refuses a commit where
`warrants.bib`'s claim count differs from the test-function count, or where warrant sections and
rubric sections disagree. The claim is **transcribed** from the test's docstring rather than
restated, because the prose was authored at the moment the defect was measured.

⚑ **AND THE RATCHET WILL REFUSE YOUR NEW DEBT.** `mikemol-ratchet <dist> --init-absent` mints the
baseline once; after that a new `file:rule` key is refused even if you paid another one down in the
same commit. That is deliberate: paying one key down while another regresses leaves the count
unchanged and the membership churned, which is the substitution a count-based gate cannot see.

## Two traps the existing distributions walked into

⚑ **`readme = "README.md"` IS DECLARED BY EVERY DISTRIBUTION AND THE FILE EXISTS IN NONE.** Ship
the file or drop the key; do not inherit the bug.

⚑ **A CLAIM IN THE ROUTING TABLE MUST NAME A TOOL THAT IS INSTALLED HERE.** `.claude/skills/
struct-tools/SKILL.md` briefly claimed `.bib` for `bibstruct`, which is not on `PATH` and not a
dependency of anything — so the gate refused a read and named a route the author could not take.
A block without a route is worse than no block.


---

## ⚑ On the number above

It read **25 of 25** until 2026-09-06, when the tree held **34**. Nine targets were added over a
day of work and nothing re-read the sentence that told a new contributor what to expect.

⚑⚑ **This document's whole purpose is telling someone how to verify their work, so a stale count
here fails in the worst direction:** a reader who runs the suite and sees a different number cannot
tell whether they broke something, whether their checkout is wrong, or whether the document is old.
**All three look identical from a fresh clone**, and the first two are alarming while only the third
is true.

⚑ It was found by a checker that flags a document carrying measurements while citing no rule to
cross-check them against — and it was found only because the population being scanned was widened
past the two files already covered. **A figure decays wherever it sits; the checker had been looking
where the figures were already known.**
