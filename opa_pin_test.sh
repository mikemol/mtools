#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W488: the opa version is written in three places; this fails unless all three agree.
# usage: opa_pin_test.sh <pytestspec opa.py> <MODULE.bazel> <pycodemod/BUILD.bazel>
# A site the extractor cannot read is a failure, never a skip: an empty match must not agree.
# The BUILD site is the string arg on the line after `location @opa//file`, in target opa_test.
set -euo pipefail
py="$(sed -n 's/^PINNED = "\([^"]*\)"$/\1/p' "$1")"
module="$(sed -n 's|.*/open-policy-agent/opa/releases/download/v\([^/]*\)/.*|\1|p' "$2")"
build="$(sed -n '/location @opa\/\/file)",$/{n;s/^ *"\([^"]*\)",$/\1/p;}' "$3")"
echo "opa.PINNED=${py:-?} MODULE.bazel=${module:-?} //pycodemod:opa_test=${build:-?}"
for v in "$py" "$module" "$build"; do
    if [ -z "$v" ] || [ "$v" != "$py" ]; then
        echo "opa pins disagree or one is unreadable" >&2
        exit 1
    fi
done
