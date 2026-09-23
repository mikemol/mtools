#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑⚑ THE ONE SHELL SPELLING OF "NO `GIT_*` SURVIVES A RUNNER". It was written three times, once in
# each of `.githooks/pre-commit`, `preflight.sh` and `domain_witness.sh` (e4a171b), and each copy's
# comment already said *same function as the gate's* — a claim three files made about each other
# and nothing checked. Sourced rather than duplicated, as `refusal_record.sh` is: a repair applied
# to one call site is not a repair to the class.
#
# ⚑⚑ THE RULE IS substrate's (`mikemol.fence.git_env.clean_env`): every name starting `GIT_`,
# nothing kept. The Python spelling lives there; this is the shell one, and there is no third.
#
# ⚑ SCOPED, NOT GLOBAL. Sourcing this file changes nothing about the caller's environment; only the
# command handed to `git_scrubbed` runs without `GIT_*`. The gate's own git calls NEED the hook's
# variables (the staged index, the residue sweep, the witness restore), so the scrub is per-launch.
# ⚑ With no `GIT_*` set, `_unset` is empty and this is exactly `env "$@"`.

git_scrubbed() {  # the command, run with every GIT_* variable removed from its environment
    local _name
    local -a _unset=()
    for _name in $(compgen -e); do
        case "$_name" in GIT_*) _unset+=(-u "$_name") ;; esac
    done
    env "${_unset[@]}" "$@"
}
