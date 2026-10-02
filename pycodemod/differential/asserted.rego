# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W402: asserted (_pycodemod_selftest.py:629-668). Each rule states the origin's own check
# against the captured result, read with libcst present (W347, W348).
#   asserted result: [literal sites, computed sites]; site rows [path, line]
# Withheld, not ruled:
#   073 compares (len(forwards hits), len(literal), len(computed)) across TWO calls; the capture
#       keeps only the latest (forwards), so half of the tuple is not in `result`. A rule over
#       the forwards half alone would be a weaker claim than the origin's.
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.asserted

import rego.v1

literal := {row[1] | some row in input.result[0][0]}

computed := {row[1] | some row in input.result[0][1]}

# line -> the bucket the origin requires it in
bucket := {
	"066-asserted-a-bare-integer-is-a-literal": [3, "literal"],
	"067-asserted-a-call-expression-is-computed": [4, "computed"],
	# a unary minus wraps a literal; without the recursive unwrap it reads computed
	"068-asserted-a-negated-literal-is-still-a-literal": [5, "literal"],
	"069-asserted-a-bare-name-is-computed": [6, "computed"],
	"071-asserted-an-interpolated-f-string-is-computed": [8, "computed"],
	"072-asserted-an-f-string-with-nothing-interpolated-is-literal": [9, "literal"],
}

in_bucket(line, "literal") if line in literal

in_bucket(line, "computed") if line in computed

deny contains sprintf("%v: line %v is not %v", [substring(input.case, 0, 3), want[0], want[1]]) if {
	want := bucket[input.case]
	not in_bucket(want[0], want[1])
}

# an absent keyword is in neither bucket; folding it into computed inflates the honest half
deny contains "070: the call not passing the keyword is in a bucket" if {
	input.case == "070-asserted-a-call-not-passing-the-keyword-is-in-neither-bucket"
	7 in literal | computed
}

judged := {c | some c, _ in bucket} | {"070-asserted-a-call-not-passing-the-keyword-is-in-neither-bucket"}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
