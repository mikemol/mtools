#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑⚑ THE TEXTUAL ROSTER CANNOT BE ENUMERATED, AND THAT WAS MEASURED RATHER THAN ASSUMED. Three
# candidate sources were tried before settling:
#
#   PATH               2,843 executables — a real population, and flagging all of it is useless.
#   `apropos -s 1 text`   86 hits — an EXTERNAL authority, written by packagers rather than by me,
#                      and the control KILLED IT: none of `hexdump`, `col`, `pr`, `look`,
#                      `base64` or `sdiff` appear, all six of which are readers added by hand.
#                      `hexdump`'s own man page says *"display file contents"*, never "text", so
#                      the vocabulary varies per packager and no keyword captures the class.
#   dpkg manifest      unavailable on this host.
#
# ⚑⚑ SO THE ROSTER IS IRREDUCIBLY HAND-WRITTEN, and pretending otherwise would have shipped a
# check built on a source that misses six of six known members. What CAN be checked is DRIFT: a
# roster entry that no longer exists on this machine is a guess nobody can verify, and a roster
# that has stopped matching the tools present is one nobody re-measured.
#
# ⚑ THIS REPORTS RATHER THAN REFUSES. A tool absent from THIS host may be present on a peer's, and
# the roster is shipped in a package other repositories adopt — so "you list something I cannot
# find" is information, not a defect.
set -uo pipefail

cd "$(dirname "$0")" || exit 1
py="hooks/.venv/bin/python3"

if [ ! -x "$py" ]; then
    echo "  UNMEASURED: $py is not executable — a fact about the reader, not the roster"
    exit 0
fi

# ⚑ THE ROSTER IS READ FROM THE MODULE, never retyped here. A checker carrying its own copy of the
# thing it verifies drifts from it silently — measured four times in this repository.
roster=$(PYTHONPATH=hooks/src "$py" -c \
    'from mikemol.hooks.structural_query import TEXTUAL; print(" ".join(sorted(TEXTUAL)))' 2>/dev/null)

if [ -z "$roster" ]; then
    echo "  UNMEASURED: could not read TEXTUAL from the module"
    exit 0
fi

absent=""
for tool in $roster; do
    command -v "$tool" >/dev/null 2>&1 || absent="$absent $tool"
done

# ⚑ COUNTED BY SPLITTING INTO AN ARRAY, not by an unquoted expansion. `printf '%s\n' $roster`
# relies on word splitting, which shellcheck flags — and quoting it counts ONE line rather than
# 51, so the naive fix is wrong in the direction that looks right.
read -ra roster_arr <<< "$roster"
total=${#roster_arr[@]}
if [ -n "$absent" ]; then
    printf '  roster: %s entries, not present here:%s\n' "$total" "$absent"
    echo "    (a peer's host may have them — the roster ships in an adopted package)"
else
    printf '  roster: %s entries, every one present on this host\n' "$total"
fi
