#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑ RUFF AS AN ACTION, BECAUSE OUTSIDE THE GRAPH IT HAS NO KEY AT ALL. The pre-commit hook ran
# `ruff` directly: no key, no invalidation, no reuse, full re-execution every commit. That is not
# the stale-green defect — a check with no key cannot serve a wrong verdict — but it is why the
# cost never falls.
#
# ⚑ ITS DOMAIN IS HAND-WRITABLE, WHICH IS WHY THIS IS AN ORDINARY sh_test AND NOT A GENERATOR.
# MEASURED: break a return type in ast.py and mypy's verdict on spans.py CHANGES while ruff's does
# not. ruff does not follow imports, so the domain is the files, the config, and the binary —
# all three declarable by hand. mypy's is `f + closure(f)` and needs computing.
#
# ⚑ REFUSES WHEN ITS TOOL IS ABSENT rather than skipping, like every other gate here.
set -euo pipefail

ruff="$(realpath "${1:?the declared ruff was not passed}")"
config="${2:?the config was not passed}"
dist="$(dirname "$config")"
config="$(basename "$config")"
shift 2

if [ ! -x "$ruff" ]; then
    echo "ruff_check: the declared ruff was not staged — refusing" >&2
    exit 1
fi
if [ "$#" -eq 0 ]; then
    echo "ruff_check: no files were staged to check — refusing" >&2
    exit 1
fi

# ⚑⚑ RUN FROM THE DISTRIBUTION DIRECTORY, NOT THE RUNFILES ROOT. `per-file-ignores` patterns like
# `tests/*` are resolved RELATIVE TO THE CONFIG, so from the runfiles root the paths arrive as
# `ratchet/tests/...` and match nothing — measured, 47 findings that the host run does not report.
# The scoped exemptions are part of the bar; a run that silently loses them is checking a
# different standard while looking like the same one.
# ⚑ `|| exit` EXPLICITLY, THOUGH `set -e` ALREADY MAKES A FAILED cd FATAL HERE. The sibling
# mypy_check.sh runs under `set -uo` without `-e` so that it can capture a nonzero rc, and there
# SC2164 was raised against the same line there — a failed cd would run the checker in the wrong
# directory and report the verdict as this distribution's. Stated the same way in both, so the
# safety does not depend on remembering which script has `-e`.
cd "$dist" || exit 1

# ⚑⚑⚑ NORMALISE THE STAGED MODE BITS, BECAUSE THE EXECUTOR INVENTS THEM. Measured, both modes:
#
#     repository        -rw-rw-r--
#     local sandbox     -rw-rw-r--     (matches; EXE002 silent)
#     remote executor   -rwxr-xr-x     (invented; EXE002 fires on EVERY source)
#
# `EXE002 The file is executable but no shebang is present` is a claim about a MODE BIT — a fact
# about the filesystem the REPOSITORY lives on. Bazel does not carry source modes into the
# executor's staged tree, so remotely the rule reads `+x` on files that are `+x` nowhere a
# developer can see: a true statement about the staging and a FALSE one about the repository. Three
# targets went red under `--config=remote` from this one cause — `ruff`, then the `ratchet` census
# over ruff's output, then `test_bar_fires`' suppression arm.
#
# ⚑⚑ OPERATOR RULING: NORMALISE THE POPULATION, NOT THE RULE. The alternatives were disabling
# `EXE002` repo-wide — which turns off a check that is CORRECT on the instrument developers
# actually run — or excluding these targets from remote, which concedes the stronger sandbox.
# This repairs the subject instead.
#
# ⚑ AND THE IDIOM IS ALREADY IN THIS TREE: `mypy_check.sh` deletes the synthesized `__init__.py`
# markers rules_python writes into a runfiles tree, for exactly this reason — an action normalising
# its own staged inputs so the checker reads the population the repository has. Measured that the
# staged files are owner-writable, so the action may do it; `|| true` because a read-only staging
# is a weaker sandbox, not a reason to refuse.
find . -name '*.py' -perm -u+x -exec chmod u-x,g-x,o-x {} + 2>/dev/null || true

exec "$ruff" check --no-cache --config "$config" .
