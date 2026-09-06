#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑⚑ THE DECLARED TEST POPULATION MUST EQUAL THE COLLECTED ONE. Starlark cannot read a Python
# file, so a per-case `py_test` needs its node-ids WRITTEN DOWN in the BUILD file — and a
# hand-written population is the defect this repository has paid for more than any other. It was
# a five-module blocker list against an enumeration of 32; it was a frozen tree roster printing
# "no mismatches" as a verdict about a repo; it was `0 of 1` reported as `0 of the world`.
#
# ⚑⚑ AND IT WOULD HAVE BEEN WRONG ON DAY ONE HERE, WHICH IS NOT A HYPOTHETICAL. This tree has 35
# `def test_` lines and collects 38 node-ids: one parametrized case expands to four. A list
# transcribed by reading the source — the obvious way to write it — omits three real cases and
# reports a green over a population three cases short.
#
# ⚑ SO THE DECLARATION IS ALLOWED, AND IT IS GATED. The BUILD file names the cases (that is what
# makes each one an action with its own key); this action proves the naming is complete. A
# declaration nothing checks is a claim; a declaration checked against the source is a schema.
set -uo pipefail

py="$(realpath "${1:?the pytest runner was not passed}")"
cfg="$(realpath "${2:?the config was not passed}")"
declared="$(realpath "${3:?the declared node-id list was not passed}")"
shift 3

# ⚑ THE COLLECTION IS THE SUBJECT, SO IT MUST NOT BE SILENTLY EMPTY. A pytest invocation that
# collects nothing exits 5, not 1 — and a naive `|| exit 1` would let the empty case through as
# a diff against an empty declared list, which compares equal when both are wrong.
collected="$("$py" -c "$cfg" --collect-only -q "$@" 2>&1 | grep '::' | sort)"
if [ -z "$collected" ]; then
    echo "collect_check: pytest collected NOTHING — refusing rather than comparing two" >&2
    echo "  empty sets, which agree for the wrong reason" >&2
    exit 1
fi

if ! diff -u <(sort "$declared") <(printf '%s\n' "$collected"); then
    echo "collect_check: the BUILD file's declared cases do not match what pytest collects" >&2
    echo "  a case above with '-' is declared and does not exist; '+' exists and is unwarranted" >&2
    echo "  by a target, so it runs in NO action and its verdict is nobody's" >&2
    exit 1
fi
printf 'collect_check: %s case(s), declared set == collected set\n' "$(printf '%s\n' "$collected" | wc -l)"
