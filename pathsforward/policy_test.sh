#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W850: `opa test` over the realizability policy and its _test.rego (every gate's witness and
# control), as a bazel test. The opa is @opa, the one MODULE.bazel pins by hash, so no version
# string is restated here. The same shape as //hooks:policy_test.
# usage: policy_test.sh <opa> <one file inside the policy directory>
set -euo pipefail
exec "$1" test "$(dirname "$2")"
