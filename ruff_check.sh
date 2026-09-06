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
exec "$ruff" check --no-cache --config "$config" .
