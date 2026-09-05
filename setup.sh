#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑⚑ A FRESH CLONE HAS NO GATES, AND LOOKS EXACTLY LIKE A REPOSITORY THAT PASSES THEM.
# `core.hooksPath` is per-clone git config, not a tracked file — measured, `git config --get
# core.hooksPath` in a fresh clone returns nothing, so `.githooks/pre-commit` sits in the tree
# and never runs. Every check this repository owns is then absent, silently, for exactly the
# reader most likely to assume it is present: someone who just cloned it.
#
# ⚑⚑ THIS SCRIPT IS THE ARMING STEP AND IT IS IDEMPOTENT. Run it once per clone. It is not a
# build step and deliberately installs nothing else: the hermetic suite needs no venvs
# (`bazel test //...` passes 25 of 25 in a tree with none), so arming the hook is the whole gap
# between a clone and a guarded checkout.
set -euo pipefail

root="$(git rev-parse --show-toplevel)"
cd "$root"

git config core.hooksPath .githooks
echo "setup: core.hooksPath = $(git config --get core.hooksPath)"

if [ ! -x .githooks/pre-commit ]; then
    echo "setup: .githooks/pre-commit is not executable — refusing" >&2
    exit 1
fi

echo "setup: armed. \`bazel test //...\` runs the hermetic suite; the hook runs it on commit."
