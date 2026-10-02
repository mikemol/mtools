# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W414: source_of (_pycodemod_selftest.py:1007-1024). Each rule states the origin's own check
# against the captured rows, read with libcst present (W347, W348).
#   source_of rows: [path, start, end, text]
# ⚑ 121's NAME and ASSERTION DISAGREE. It is called "finds a class as well as a function", but it
# asserts `bool(source_of("V", [<d>/nope.py])) is False`: a name in a file that does not exist
# yields nothing. No class is in the fixture. The rule states what the assertion measures (an
# absent file is an empty result, not an error); the class claim is untested in the origin and is
# recorded as an origin finding (W36-differential.md), not invented here.
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.source

import rego.v1

rows := input.result[0]

# the extent comes from the CST, not a line window
deny contains "118: the extent is not exactly one def at lines 3-5" if {
	input.case == "118-source-returns-exactly-one-def-with-its-cst-extent"
	[[row[1], row[2]] | some row in rows] != [[3, 5]]
}

deny contains "119: the body text lacks its comment" if {
	input.case == "119-source-returns-the-body-text-comments-included"
	not contains(rows[0][3], "⚑ a comment inside the body")
}

# the direction a naive "print N lines" fails
deny contains "120: the text swallows the following def" if {
	input.case == "120-source-does-not-swallow-the-following-def"
	contains(rows[0][3], "after")
}

deny contains "121: a name in a nonexistent file yields rows" if {
	input.case == "121-source-finds-a-class-as-well-as-a-function"
	rows != []
}

judged := {
	"118-source-returns-exactly-one-def-with-its-cst-extent",
	"119-source-returns-the-body-text-comments-included",
	"120-source-does-not-swallow-the-following-def",
	"121-source-finds-a-class-as-well-as-a-function",
}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
