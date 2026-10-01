#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑⚑ THE MUTATION GRID AS A GATE TARGET, ONE PER DISTRIBUTION — operator ruling 2026-09-13,
# re-confirmed the same day against a corrected cost range. The DAG decides when it re-runs: a
# distribution whose sources are unchanged is a cache hit and costs nothing, so the whole-tree worst
# case is paid once and then only where something moved.
#
# ⚑⚑⚑ THIS FILE IS THE SECOND WRITING. The first was shellcheck-clean, ran the grid outside bazel,
# and lived in a scratchpad directory that an OS change erased on 2026-09-19 along with every other
# probe this tree had built that week. A handle only survives if its referent lives outside the
# context; this one now does.
#
# ⚑⚑ THE COST IS A RANGE, NOT A NUMBER. One mdstruct cell measured 1.4s on a quiet machine and 23.6s
# at load average 48.65 — a 17x spread, and both figures were taken through interpreters that have
# since been removed twice. The operator was shown the range and ruled to wire it anyway: the DAG is
# what makes the worst case rare. The figure that survives a load spike is a RATIO measured in one
# minute (bazel-built venv ~18% slower than host), not an absolute second-count.
#
# ⚑⚑⚑ THE INTERPRETER IS DERIVED, NOT PASSED, AND IT IS NEVER `realpath`'d. Two lessons, each paid
# for at length:
#   1. bazel refuses `$(location :.venv)` because that target expands to every staged file (2,225 of
#      them for ratchet), so no single-file expression can name `bin/python3`. `dirname` of the config
#      is the distribution root under whatever prefix the package is staged at.
#   2. A venv works precisely BECAUSE its interpreter is invoked through its own `bin/` path — that is
#      what sets `sys.prefix`. Dereferencing the symlink hands back the base interpreter with no venv,
#      and every mutant then runs without the distribution's dependencies. `mypy_check.sh` does
#      `realpath` on ITS interpreter safely, because that one is a staged `py_binary`; here it is the
#      defect. It hid for three ticks behind an asymmetry: `ratchet` and `fence` declare
#      `dependencies = []` and pass under a bare interpreter, so two of four distributions cannot
#      detect it at all. **F-ARM THIS ON mdstruct, never on ratchet.**
set -uo pipefail

config="${1:?the config was not passed}"
runner="${2:?the runner was not passed}"

dist="$(dirname "$config")"
py="$dist/.venv/bin/python3"

# ⚑⚑ THE INTERPRETER IS THE SUBJECT OF ITS OWN PRECONDITION, and this check earned itself on its
# first real use: `//ratchet:mutants` failed in 0.6s with this exact line, because `.venv` had not
# been staged into the runfiles tree. Without it the grid would have run under whatever `python3`
# the sandbox provides — reporting every site ERRORED, which reads as *the suite did not run* rather
# than *the harness is misconfigured*. That ambiguity cost three ticks once; the refusal converts it
# into one line naming the missing path.
if [ ! -x "$py" ]; then
    echo "mutate_check: $py was not staged — refusing rather than running a grid" >&2
    echo "  under whatever interpreter happens to be on PATH" >&2
    exit 1
fi

# ⚑⚑⚑ UNDER BAZEL'S SANDBOX THE INTERPRETER IS A HARDLINK, NOT A LINK, and it cannot find its own
# stdlib: bazel resolves the venv's symlink at staging (printed from a kept sandbox, 2026-09-19),
# so CPython has nothing to follow and `pyvenv.cfg`'s `home` names the venv's own `bin/`. The
# toolchain IS staged — at `$RUNFILES_DIR/<repo>/` — and `PYTHONHOME` is the one mechanism that
# names it without baking a path into an artifact. The repo name is written by `venv.bzl` beside
# `pyvenv.cfg`; outside a runfiles tree the symlink resolves on its own and nothing is set.
if [ -n "${RUNFILES_DIR:-}" ] && [ -r "$dist/.venv/pythonhome.runfiles" ]; then
    PYTHONHOME="$RUNFILES_DIR/$(cat "$dist/.venv/pythonhome.runfiles")"
    export PYTHONHOME
fi

# ⚑⚑ A DECLARED TOOL PATH IS RUNFILES-RELATIVE, AND THE RUNNER LEAVES THE RUNFILES TREE. bazel
# expands `$(location @pandoc//:bin)` relative to the test's cwd; the grid copies the tree to a
# temp directory and runs pytest THERE, where the relative path names nothing. MEASURED
# 2026-09-19: 64 of 64 mdstruct sites ERRORED the moment `conftest` stopped falling back to PATH
# under bazel — which also settled that the earlier 64 KILLED had been running the HOST's pandoc.
# Absolutised here, once, before the cwd changes; unset stays unset (a host run has no
# declaration and `conftest` reads PATH there, honestly).
if [ -n "${PANDOC_BIN:-}" ] && [ "${PANDOC_BIN#/}" = "$PANDOC_BIN" ]; then
    PANDOC_BIN="$PWD/$PANDOC_BIN"
    export PANDOC_BIN
fi

# ⚑ AND `-x` IS NECESSARY, NOT SUFFICIENT. A dangling symlink is mode 775 and `-x`-true right up
# until `execve` refuses it — measured on 2026-09-16 when a whole interpreter root was removed. The
# grid below RUNS the interpreter, and its verdict is what settles whether the venv is real.
out="$("$py" "$runner" "$py" "$config" 2>&1)"
rc=$?
printf '%s\n' "$out"

if [ "$rc" -ne 0 ]; then
    echo "mutate_check: the grid REFUSED — a SURVIVED site means nothing exercises it, and an" >&2
    echo "  ERRORED site means the grid is incomplete and its clean list is a claim over a" >&2
    echo "  population that was never measured" >&2
    exit 1
fi

# ⚑ A GREEN OVER NO OUTPUT IS THE GREEN-OVER-NOTHING SHAPE THIS REPOSITORY EXISTS TO REFUSE. The
# runner prints every category by name even when empty, so silence here means it never ran.
if [ -z "$out" ]; then
    echo "mutate_check: the grid produced NO output — refusing rather than reporting a green" >&2
    echo "  over a check that may not have run" >&2
    exit 1
fi
