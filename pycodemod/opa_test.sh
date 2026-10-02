#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W478: `opa test` over pycodemod/differential's Rego specs and their _test.rego, as a bazel test.
# usage: opa_test.sh <opa> <pinned-version> <one file inside differential/>
# An opa that is not the pinned version is a failure, never a skip.
set -euo pipefail
opa="$1"
pinned="$2"
dir="$(dirname "$3")"
version="$("$opa" version | sed -n 's/^Version: //p')"
if [ "$version" != "$pinned" ]; then
    echo "opa is ${version:-unknown}, not the pinned $pinned" >&2
    exit 1
fi
exec "$opa" test --ignore "*.json" "$dir"
