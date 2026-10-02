# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W400: ambient (_pycodemod_selftest.py:3028-3092). Each rule states the origin's own check
# against the captured rows, read with libcst present (W347, W348). The origin keys rows by
# enclosing def (`ctx`), so the rules do too.
#   ambient rows: [path, line, kind, verdict, text, ctx]
# Withheld, not ruled:
#   407 judges the module constant KNOWN_MISSES; no call returns it.
#   408 judges ambient.population, an attribute the function stamps on itself; the capture
#       never keeps it (the W226/W399 class).
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.ambient

import rego.v1

rows := input.result[0]

verdict_by_ctx := {row[5]: row[3] | some row in rows}

# anchored and PATH-resolved calls are not ambient reads: no row at all
no_row := {
	"399-a-join-onto-root-is-anchored-no-row": "anchored",
	"400-abspath-file-is-anchored-no-row": "anchored_file",
	"403-a-bare-command-name-is-path-resolved-not-cwd-relative-no-row": "command",
}

deny contains sprintf("%v: %v has a row; it is not an ambient read", [substring(input.case, 0, 3), ctx]) if {
	ctx := no_row[input.case]
	verdict_by_ctx[ctx]
}

verdict := {
	"401-a-path-that-is-the-function-s-own-parameter-is-scoped-the-fe": ["scoped", "SCOPED"],
	"402-a-repo-relative-literal-is-repo-the-defect-class": ["repo_relative", "REPO"],
	"404-but-a-relative-script-path-in-argv-0-still-reports": ["rel_script", "REPO"],
	"405-an-explicit-source-argument-makes-the-call-scoped": ["explicit_source", "SCOPED"],
	"406-os-chdir-is-its-own-verdict-it-mutates-the-thing-under-study": ["mutate", "MUTATES"],
}

deny contains sprintf("%v: %v does not read %v", [substring(input.case, 0, 3), want[0], want[1]]) if {
	want := verdict[input.case]
	object.get(verdict_by_ctx, want[0], null) != want[1]
}

judged := {c | some c, _ in no_row} | {c | some c, _ in verdict}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
