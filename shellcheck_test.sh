#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑ THE BINARY IS THE DECLARED ONE, NOT WHATEVER PATH OFFERS. A hermetic action that reached for
# PATH would check the shell with a tool nobody declared — the same sandbox escape this repository
# refuses for editable installs, one layer over. If the staged binary is missing this REFUSES
# rather than skipping, because a skip here reports green over a check that never ran.
set -euo pipefail

# ⚑ THE PATHS ARE PASSED BY BAZEL VIA `$(location ...)`, not searched for. A `find` over the
# runfiles tree looked equivalent and was not: an external repository's files are not rooted in
# the test's own directory, so the search returned nothing and the guard below correctly refused
# — a red gate for a reason unrelated to the shell it exists to check.
sc="${1:?the declared shellcheck was not passed}"
shift

if [ ! -x "$sc" ]; then
    echo "shellcheck_test: the declared shellcheck was not staged — refusing" >&2
    exit 1
fi
if [ "$#" -eq 0 ]; then
    echo "shellcheck_test: no shell files were staged to check — refusing" >&2
    exit 1
fi
for target in "$@"; do
    if [ ! -f "$target" ]; then
        echo "shellcheck_test: $target was not staged — refusing" >&2
        exit 1
    fi
done

# ⚑⚑⚑ THE PASS PATH EMITTED ZERO BYTES, SO A RUN AND A NON-RUN WERE BYTE-IDENTICAL. MEASURED on
# a clean file: 0 bytes, exit 0. `shellcheck` says nothing when it finds nothing and this script
# ends in `exec`, so there was nothing to say it had happened. That is the shape refused in every
# other gate here — `preflight.sh` refuses a missing tool rather than skipping, `rule_citations.sh`
# keeps a pass line SPECIFICALLY so a run is distinguishable from a non-run — and it was sitting
# in the gate that checks the shell those refusals are written in.
#
# ⚑⚑ THE COUNT IS THE FIGURE, AND IT MOVES. Targets arrive from bazel's `$(location …)` expansion,
# so *how many files were staged* is exactly what a silent pass hides: a glob that stopped matching
# would stage FEWER files and still exit 0 with no output. The comment above records that a
# `find`-based version once returned NOTHING and was caught only because the guard refused an
# empty list — the count is the reading that would have named it rather than merely stopping it.
#
# ⚑ BEFORE THE `exec`, NOT AFTER. After it this shell does not exist; a line written below would
# never run, which is the same defect wearing a fix.
echo "shellcheck_test: checked $# shell file(s) with $(basename "$sc")"

# ⚑ EXCLUDE IS EMPTY. Waivers are measured here, never inherited from a peer.
exec "$sc" "$@"
