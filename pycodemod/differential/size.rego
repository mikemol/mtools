# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W406: module_size / module_size_all (_pycodemod_selftest.py:1288-1325). Each rule states the
# origin's own check against the captured result, read with libcst present (W347, W348).
#   result: [rows, n]
#   module_size rows:     [path, code_lines, ..., ..., why]
#   module_size_all rows: [path, code_lines, ..., ..., why, cap, incidents, physical_lines]
# The physical count is APPENDED (index 7) so why/cap keep their positions (4, 5).
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.size

import rego.v1

rows := input.result[0][0]

# two __main__ guards fire at a threshold SIZE cannot reach
deny contains "145: two __main__ guards are not exactly one row" if {
	input.case == "145-two-main-guards-are-reported-at-any-size"
	count(rows) != 1
}

deny contains "146: the reason does not name the two guards" if {
	input.case == "146-and-the-reason-names-them"
	not contains(rows[0][4], "2 __main__ guards")
}

empty := {
	# a single guard is every ordinary CLI
	"147-one-main-guard-is-not-a-finding",
	# comments are the corpus's incident log, not bulk
	"148-comment-lines-are-not-counted-as-bulk",
}

deny contains sprintf("%v: a row is reported where none may be", [substring(input.case, 0, 3)]) if {
	input.case in empty
	rows != []
}

column := {
	"149-but-the-physical-count-is-reported-alongside": [[7], [501]],
	"150-and-the-code-count-still-excludes-them": [[1], [1]],
	"151-at-the-end-of-the-row-so-no-existing-index-shifts": [[4, 5], ["", 100]],
}

deny contains sprintf("%v: columns %v read %v, not %v", [substring(input.case, 0, 3), want[0], got, want[1]]) if {
	want := column[input.case]
	got := [rows[0][i] | some i in want[0]]
	got != want[1]
}

judged := {
	"145-two-main-guards-are-reported-at-any-size",
	"146-and-the-reason-names-them",
} | empty | {c | some c, _ in column}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
