#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W342: run venv_check.py over ONE distribution's built .venv, from inside that distribution's own
# bazel test. The interpreter is DERIVED from the config's directory, as mutate_check.sh derives
# it: bazel cannot name `bin/python3` inside `:.venv` with a single $(location), and the venv works
# only when invoked through its own bin/, so it is never realpath'd.
#
# ⚑ UNDER BAZEL'S SANDBOX THE INTERPRETER IS A HARDLINK that finds its stdlib only through
# PYTHONHOME, set from the repo name venv.bzl writes beside pyvenv.cfg. mutate_check.sh measured
# this (2026-09-19). Outside a runfiles tree the symlink resolves and nothing is set.
set -uo pipefail

config="${1:?the config was not passed}"
check="${2:?venv_check.py was not passed}"

dist="$(dirname "$config")"
venv="$dist/.venv"
py="$venv/bin/python3"

if [ ! -x "$py" ]; then
    echo "venv_check: $py was not staged; refusing rather than checking nothing" >&2
    exit 1
fi

if [ -n "${RUNFILES_DIR:-}" ] && [ -r "$venv/pythonhome.runfiles" ]; then
    PYTHONHOME="$RUNFILES_DIR/$(cat "$venv/pythonhome.runfiles")"
    export PYTHONHOME
fi

name="$(basename "$(cd "$dist" && pwd)")"
"$py" "$check" "$venv" "$name" "$dist"
rc=$?
if [ "$rc" -eq 0 ]; then
    echo "venv_check: $name's venv holds every check"
fi
exit "$rc"
