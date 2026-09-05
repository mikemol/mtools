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

# ⚑ EXCLUDE IS EMPTY. Waivers are measured here, never inherited from a peer.
exec "$sc" "$@"
