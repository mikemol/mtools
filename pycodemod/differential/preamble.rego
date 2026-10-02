# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W419: the losslessness preamble (_pycodemod_selftest.py:108-121), the cases before the first
# `# ──` mode header. 001 is declared unmeasured in gen_cases.py (capture class `none`: it calls
# libcst directly, no pycodemod mode). Each other rule states the origin's own check.
#   roundtrip result: [identical, reason]
#   scan rows:        [path, kind, name, line]
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.preamble

import rego.v1

rows := input.result[0]

deny contains "002: roundtrip does not accept the well-formed file" if {
	input.case == "002-roundtrip-accepts-a-well-formed-file"
	rows[0] != true
}

kind_lines := {[row[1], row[3]] | some row in rows}

found := {
	"003-a-def-is-found": ["def", 2],
	"004-a-call-is-found": ["call", 7],
}

deny contains sprintf("%v: (%v, %v) is not found", [substring(input.case, 0, 3), want[0], want[1]]) if {
	want := found[input.case]
	not want in kind_lines
}

judged := {"002-roundtrip-accepts-a-well-formed-file"} | {c | some c, _ in found}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
