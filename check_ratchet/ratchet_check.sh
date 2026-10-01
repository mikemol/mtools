#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑ THE RATCHET AS AN ACTION. Outside the graph it had no key at all — full re-execution every
# commit, nothing reused. Its domain is the distribution's sources, its config, the ruff binary
# and THE BASELINE FILE, all declared by the target that invokes this.
#
# ⚑ THE BASELINE IS THE PART A CARELESS DECLARATION WOULD DROP, and dropping it is the interesting
# failure: the census would be keyed while the thing it is compared AGAINST would not, so editing
# the baseline would not invalidate the verdict. A ratchet whose baseline sits outside its own key
# can be lowered with no gate noticing — the laundering `--init-absent` refuses on a second run.
#
# ⚑ IT SHARES SOURCES WITH THE `ruff` TARGET AND IS NOT DUPLICATE WORK: that one runs
# `ruff check`, this one runs `ruff check --preview`. Different argv is a different action key, so
# these are two actions over one input set rather than one action run twice.
set -uo pipefail

py="$(realpath "${1:?the ratchet CLI was not passed}")"
ruff="$(realpath "${2:?the declared ruff was not passed}")"

# ⚑⚑ THE DISTRIBUTION IS THE CONFIG'S DIRECTORY. `$(location :pyproject.toml)` names a FILE and
# the CLI censuses a DIRECTORY. A first cut passed the file straight through; the run produced no
# output and the target reported PASS — a vacuous green, in a repository whose subject is vacuous
# greens.
dist="$(dirname "$(realpath "${3:?the distribution was not passed}")")"

for tool in "$py" "$ruff"; do
    if [ ! -x "$tool" ]; then
        echo "ratchet_check: $tool was not staged — refusing" >&2
        exit 1
    fi
done

# ⚑ RUFF_BIN NAMES THE DECLARED BINARY rather than letting the census reach for a developer venv,
# which is the same discipline the pandoc and stubtest witnesses use.
export RUFF_BIN="$ruff"

# ⚑⚑⚑ EXCLUDE THE RUNFILES TREE'S SYNTHESIZED `__init__.py` FILES. rules_python CREATES them so a
# runfiles tree is importable; they do not exist in the source tree, and one of them —
# `src/mikemol/__init__.py` — is the very file PEP 420 forbids here, because it would make the
# first-installed distribution the exclusive owner of the `mikemol` prefix.
#
# MEASURED: the first honest run of this gate REFUSED 8 keys, all from those synthesized files.
# The census was correct about what it saw; what it saw was not the distribution. An action whose
# domain includes artifacts the baseline was never computed over is mis-typed in the direction
# nobody checks — its inputs are a SUPERSET of the real ones, so it fails loudly rather than
# serving a stale green, which is the better of the two ways to be wrong.

# ⚑⚑ THE OUTPUT IS ECHOED AND THE EXIT CODE IS CHECKED EXPLICITLY. `exec` under `set -e` swallowed
# both, which is how the first cut passed while doing nothing. A gate must say what it found, and
# an empty transcript is itself a finding worth being able to see.
out="$("$py" "$dist" 2>&1)"
rc=$?
printf '%s\n' "$out"
if [ "$rc" -ne 0 ]; then
    echo "ratchet_check: the ratchet REFUSED in $dist" >&2
    exit 1
fi
if [ -z "$out" ]; then
    echo "ratchet_check: the ratchet produced NO output — refusing rather than reporting a" >&2
    echo "  green over a census that may not have run" >&2
    exit 1
fi
