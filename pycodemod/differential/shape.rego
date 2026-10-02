# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W401: shape_sites / roundtrip (_pycodemod_selftest.py:1606-1653). Each rule states the origin's
# own check against the captured result, read with libcst present (W347, W348). 191 and 192 are
# sticky, but onto the same shape_sites call the origin reads (`hits`), so they are measured.
#   shape_sites rows: [path, line, text]
#   roundtrip result: [identical, reason]
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.shape

import rego.v1

rows := input.result[0]

lines := [row[1] | some row in rows]

deny contains "190: the code site is not exactly line 3, `x = ...`" if {
	input.case == "190-shape-locates-the-code-site-by-line"
	[[row[1], startswith(row[2], "x =")] | some row in rows] != [[3, true]]
}

# prose is not a site
prose_line := {
	"191-a-docstring-mention-is-not-a-site": 1,
	"192-a-comment-mention-is-not-a-site": 2,
}

deny contains sprintf("%v: prose at line %v is reported as a site", [substring(input.case, 0, 3), line]) if {
	line := prose_line[input.case]
	line in lines
}

deny contains "193: --shape-all does not include the prose mentions" if {
	input.case == "193-shape-all-includes-prose"
	count(rows) < 3
}

deny contains "194: a code line with a trailing comment is excluded" if {
	input.case == "194-a-code-line-with-a-trailing-comment-is-not-excluded"
	count(rows) == 0
}

# anchored patterns: the exact lines each finds
anchored := {
	"195-a-anchored-pattern-finds-the-column-0-site": [1],
	"196-a-anchored-pattern-excludes-the-indented-site": [3],
	"197-if-name-locates-the-entry-point": [4],
}

deny contains sprintf("%v: the anchored pattern finds %v, not %v", [substring(input.case, 0, 3), lines, want]) if {
	want := anchored[input.case]
	lines != want
}

deny contains "198: a syntax error is not a false verdict" if {
	input.case == "198-a-syntax-error-is-a-verdict-not-a-crash"
	rows[0] != false
}

judged := {
	"190-shape-locates-the-code-site-by-line",
	"193-shape-all-includes-prose",
	"194-a-code-line-with-a-trailing-comment-is-not-excluded",
	"198-a-syntax-error-is-a-verdict-not-a-crash",
} | {c | some c, _ in prose_line} | {c | some c, _ in anchored}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
