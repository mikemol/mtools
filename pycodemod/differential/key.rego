# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W412: key_reads (_pycodemod_selftest.py:1033-1060). Each rule states the origin's own check
# against the captured rows, read with libcst present (W347, W348).
#   key_reads rows: [path, line, kind, ctx]
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.key

import rego.v1

rows := input.result[0]

line_kinds := sort([[row[1], row[2]] | some row in rows])

exact := {
	# three CST shapes for one question: subscript, .get, `in`
	"122-key-finds-the-subscript-the-get-and-the-in-test": [[4, "read"], [5, "read"], [6, "read"]],
	# folding decl into read would make every declared field look used
	"125-a-literal-in-a-schema-tuple-is-a-decl-not-a-read": [[2, "decl"], [8, "read"]],
}

deny contains sprintf("%v: rows are %v, not %v", [substring(input.case, 0, 3), line_kinds, want]) if {
	want := exact[input.case]
	line_kinds != want
}

deny contains "123: the context is not exactly {project}" if {
	input.case == "123-key-reports-the-enclosing-function-as-context"
	{row[3] | some row in rows} != {"project"}
}

deny contains "124: a docstring mention is reported as a read" if {
	input.case == "124-a-key-named-in-a-docstring-is-not-a-read"
	rows != []
}

deny contains "126: the never-read field is not exactly one decl" if {
	input.case == "126-a-declared-but-never-read-field-is-visible-as-decl-with-no-r"
	[row[2] | some row in rows] != ["decl"]
}

judged := {c | some c, _ in exact} | {
	"123-key-reports-the-enclosing-function-as-context",
	"124-a-key-named-in-a-docstring-is-not-a-read",
	"126-a-declared-but-never-read-field-is-visible-as-decl-with-no-r",
}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
