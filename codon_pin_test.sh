#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# The pinned Codon is the one the typed-subset gate is calibrated against (mtools:W1320, W1319).
# Three witnesses, so a green result says more than "the file downloaded":
#   1. the binary reports the pinned version, 0.20.3;
#   2. a small typed program compiles and runs and prints the value it should (a positive control:
#      the tool can accept what it is meant to accept);
#   3. `from __future__ import annotations` is REJECTED, as nemik measured on 0.20.3 (nemik:W560):
#      the rejection the gate will rely on is reproducible here, not only reported.
# usage: codon_pin_test.sh CODON_BINARY
set -eu

codon="$1"
want="0.20.3"

got="$("$codon" --version)"
if [ "$got" != "$want" ]; then
    echo "codon_pin_test: the pinned codon reports '$got', not '$want'" >&2
    exit 1
fi

work="$(mktemp -d "${TEST_TMPDIR:-.}/codon.XXXXXX")"
trap 'rm -rf "$work"' EXIT

cat >"$work/typed.py" <<'PY'
def add(a: int, b: int) -> int:
    return a + b


print(add(2, 3))
PY

out="$("$codon" run "$work/typed.py")"
if [ "$out" != "5" ]; then
    echo "codon_pin_test: a typed program printed '$out', not '5'" >&2
    exit 1
fi

cat >"$work/future.py" <<'PY'
from __future__ import annotations


def add(a: int, b: int) -> int:
    return a + b


print(add(2, 3))
PY

if "$codon" run "$work/future.py" >"$work/future.out" 2>&1; then
    echo "codon_pin_test: 'from __future__ import annotations' was accepted; the census assumes it is not" >&2
    exit 1
fi
if ! grep -q "__future__" "$work/future.out"; then
    echo "codon_pin_test: the future import failed, but not for its name:" >&2
    cat "$work/future.out" >&2
    exit 1
fi
echo "codon_pin_test: ok ($got)"
