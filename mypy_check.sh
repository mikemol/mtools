#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑⚑ ONE ACTION PER DISTRIBUTION, DECLARING THAT DISTRIBUTION'S WHOLE CLOSURE — and the grain was
# MEASURED rather than chosen by analogy to a peer with 2,254 targets.
#
# ⚑⚑ THE ARGUMENT IS STRUCTURAL AND THE SECONDS WERE A PROXY FOR IT. This block previously read
# `0.12s` for the whole distribution against `~3.0s` for 27 per-file actions. Those figures are
# properties of one machine at one moment; the property that decides the grain is not:
#
#     mypy ANALYSES A CLOSURE, not a file. Running it once over 27 files analyses the closure once.
#     Running it 27 times analyses THE SAME CLOSURE 27 TIMES, plus 27 interpreter startups.
#
# So per-file actions here multiply the dominant work by the file count while buying invalidation
# precision the influence cones make partly redundant anyway (`ast` is imported by 4 of 27 files,
# `spans` by 5 — counts, not timings). ⚑ A peer runs 2,254 per-file targets because at ITS scale
# the closure is not shared across the population, which reverses the same structural argument
# rather than a different arithmetic.
#
# ⚑⚑ THE DOMAIN IS THE SAME EITHER WAY, WHICH IS WHY THIS IS STILL Π-TYPED. mypy's verdict on a
# file depends on the types of everything it imports — measured: break a return type in ast.py and
# spans.py's verdict flips without spans.py being edited. Declaring the whole distribution states a
# domain that CONTAINS every file's closure, so no verdict here can be served for a key that omits
# something it read. Per-file with a computed closure would be the same property, stated tighter.
#
# ⚑ AND THE DIRECTION OF ERROR MATTERS. A domain too WIDE over-invalidates and fails loudly; a
# domain too NARROW serves a stale green. This is deliberately the wide one, at a scale where the
# whole closure is analysed in one action either way — so wideness costs an invalidation, not an
# analysis.
set -uo pipefail

py="$(realpath "${1:?the interpreter was not passed}")"
dist="$(dirname "$(realpath "${2:?the config was not passed}")")"

if [ ! -x "$py" ]; then
    echo "mypy_check: $py was not staged — refusing" >&2
    exit 1
fi

# ⚑ `|| exit` BECAUSE A FAILED cd WOULD RUN mypy IN THE WRONG DIRECTORY — checking a tree nobody
# asked about and reporting the verdict as this distribution's. shellcheck SC2164 caught it.
cd "$dist" || exit 1

# ⚑⚑⚑ REMOVE THE SYNTHESIZED PACKAGE MARKERS BEFORE CHECKING. rules_python writes an empty
# `__init__.py` at every level of a runfiles tree so it is importable — including
# `src/mikemol/__init__.py`, the file PEP 420 forbids here because it would make the
# first-installed distribution the exclusive owner of the `mikemol` prefix.
#
# MEASURED: with them present mypy reported "Success: no issues found in 1 source file" for a
# distribution of eight, resolving `src/__init__.py` as module `__main__` and `src/mikemol/
# __init__.py` as `mikemol`. A green over one file out of eight is the domain-too-NARROW defect —
# it reports success having checked almost nothing, which is the direction that serves a stale
# green rather than failing loudly.
#
# ⚑ ONLY THE EMPTY ONES, and that discriminator is the same one census.py needed: a synthesized
# marker is empty, a hand-written package `__init__.py` has content and is part of the
# distribution. Deleting by name would delete real files.
find src tests -name '__init__.py' -size 0 -delete 2>/dev/null || true

out="$("$py" 2>&1)"
rc=$?
printf '%s\n' "$out"
if [ "$rc" -ne 0 ]; then
    echo "mypy_check: mypy REFUSED in $dist" >&2
    exit 1
fi
if [ -z "$out" ]; then
    echo "mypy_check: mypy produced NO output — refusing rather than reporting a green" >&2
    echo "  over a check that may not have run" >&2
    exit 1
fi
