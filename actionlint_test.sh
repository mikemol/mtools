#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑ THE REUSABLE GATE WORKFLOW UNDER A PINNED actionlint (W332). Arguments, all from bazel's
# `$(location ...)`: actionlint, shellcheck, the actionlint config, then the workflow files.
#
# ⚑⚑ THE CHECKER IS ARMED EVERY RUN, NOT ONCE BY HAND. Before checking the real files, each one is
# copied with an unknown top-level key appended and actionlint MUST reject the copy. A binary that
# accepted anything (wrong file, wrong mode, a config that silenced the check) would turn this
# test green over nothing; the planted copy is what tells a run from a non-run.
set -euo pipefail

al="${1:?the declared actionlint was not passed}"
sc="${2:?the declared shellcheck was not passed}"
cfg="${3:?the actionlint config was not passed}"
shift 3

for tool in "$al" "$sc"; do
    if [ ! -x "$tool" ]; then
        echo "actionlint_test: $tool was not staged — refusing" >&2
        exit 1
    fi
done
if [ "$#" -eq 0 ]; then
    echo "actionlint_test: no workflow files were staged to check — refusing" >&2
    exit 1
fi

scratch="${TEST_TMPDIR:?not run under bazel test}"
for wf in "$@"; do
    if [ ! -f "$wf" ]; then
        echo "actionlint_test: $wf was not staged — refusing" >&2
        exit 1
    fi
    planted="$scratch/planted-$(basename "$wf")"
    cp "$wf" "$planted"
    printf 'not-a-workflow-key: 1\n' >>"$planted"
    if "$al" -no-color -config-file "$cfg" -shellcheck "$sc" "$planted" >"$scratch/planted.out" 2>&1; then
        echo "actionlint_test: actionlint ACCEPTED $wf with an unknown key planted — the check is not armed" >&2
        exit 1
    fi
    if ! grep -q 'not-a-workflow-key' "$scratch/planted.out"; then
        echo "actionlint_test: the planted copy of $wf failed for some other reason:" >&2
        cat "$scratch/planted.out" >&2
        exit 1
    fi
done

echo "actionlint_test: armed on $# file(s); checking them with $(basename "$al") + $(basename "$sc")"
exec "$al" -no-color -config-file "$cfg" -shellcheck "$sc" "$@"
