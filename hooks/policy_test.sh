#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W238: `opa test` over the standing policy and its _test.rego (every rule's witness and control),
# as a bazel test. The opa is @opa, the one MODULE.bazel pins by hash, so no version string is
# restated here (opa_pin_test.sh guards the sites that do restate it).
# usage: policy_test.sh <opa> <one file inside hooks/policy/>
set -euo pipefail
exec "$1" test "$(dirname "$2")"
