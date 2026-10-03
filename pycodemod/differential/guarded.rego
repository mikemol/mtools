# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W498 (from the W196 draft): guarded (_pycodemod_selftest.py:142-150), origin checks 005-008,
# over one fixture. Each rule states what COMPLIANT output is for its case, so row order never
# matters.
#   result: [[under, top]]; under rows [path, line, conds], top rows [path, line]
#
# ⚑ 008 IS A PORT-FIX (W197), stated as the compliant row, not the origin's. The `else` body runs
# exactly when `c` is FALSE, so the origin's un-negated `c` tells a gate that a call in the `else`
# of `if apply:` runs under `apply` (arguments.py:102). The origin's own check 008 pins its row
# as "over-reported under its if, never negated": that is the reference's KNOWN behaviour, so the
# reference is DENIED by rule 008 here, faithfully, and the subject is admitted. The case carries
# no `expect`: pytestspec's expect is implementation-blind, and an expect.deny would assert the
# subject is denied too, which is false.
#
# W210 (elif chains negate EVERY earlier test, then their own) has no captured case: the origin
# fixture has no elif. It stays residue until a case is captured; `negated` below is its form.
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.guarded

import rego.v1

under := input.result[0][0]

top_lines := {row[1] | some row in input.result[0][1]}

conds_at(l) := [row[2] | some row in under; row[1] == l]

# the condition an `else` (or a later elif branch) carries for a test it did not take
negated(test) := sprintf("not (%v)", [test])

deny contains sprintf("005: top lines are %v, not {2}", [top_lines]) if {
	input.case == "005-guarded-an-unconditional-call-is-top"
	top_lines != {2}
}

deny contains sprintf("006: line 4 is guarded by %v, not [[apply]]", [conds_at(4)]) if {
	input.case == "006-guarded-a-call-under-if-carries-its-test"
	conds_at(4) != [["apply"]]
}

deny contains sprintf("007: line 7 is guarded by %v, not [[a, b]] outermost-first", [conds_at(7)]) if {
	input.case == "007-guarded-nested-conditions-are-outermost-first"
	conds_at(7) != [["a", "b"]]
}

# PORT-FIX (W197): the else body is reported under the NEGATED test
deny contains sprintf("008: line 11 is guarded by %v, not [[%v]]", [conds_at(11), negated("c")]) if {
	input.case == "008-guarded-else-body-over-reported-under-its-if-never-negated"
	conds_at(11) != [[negated("c")]]
}

judged := {
	"005-guarded-an-unconditional-call-is-top",
	"006-guarded-a-call-under-if-carries-its-test",
	"007-guarded-nested-conditions-are-outermost-first",
	"008-guarded-else-body-over-reported-under-its-if-never-negated",
}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
