# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed (W398): the reference's own rows are admitted, and each rule denies the defect it
# names. Rows are the ones the libcst-present replay returned (W390-peek.py reifies).
package pycodemod.reifies_test

import rego.v1

import data.pycodemod.reifies as rf

census := [[
	["<root>/reify_case.py", 3, "lit_set", "set", "returns-literal"],
	["<root>/reify_case.py", 6, "lit_dict", "dict", "returns-literal"],
	["<root>/reify_case.py", 9, "comp_set", "set", "returns-comp"],
	["<root>/reify_case.py", 12, "comp_dict", "dict", "returns-comp"],
	["<root>/reify_case.py", 15, "call_set", "set", "returns-call"],
	["<root>/reify_case.py", 18, "call_sorted", "sorted", "returns-sorted"],
	["<root>/reify_case.py", 24, "accum", "accum", "returns-accum"],
	["<root>/reify_case.py", 30, "accum_dict", "accum", "returns-accum"],
]]

test_reference_admitted if {
	every c in rf.judged {
		rf.admitted with input as {"case": c, "result": census}
	}
}

# every positive row folded to the coarsest why: a census that cannot tell them apart
coarse := [[[r[0], r[1], r[2], "set", "returns-call"] | some r in census[0]]]

test_every_positive_denies_a_folded_why if {
	positives := {c | some c, _ in rf.reified} - {"375-return-set-xs-is-a-call-built-reification"}
	every c in positives {
		count(rf.deny) == 1 with input as {"case": c, "result": coarse}
	}
	count(rf.deny) == 1 with input as {"case": "375-return-set-xs-is-a-call-built-reification", "result": [[]]}
}

# a predicate that accepts everything: every negative appears as a row
test_every_negative_denies_an_accept_all if {
	accept_all := [array.concat(census[0], [
		["<root>/reify_case.py", 33, "streams", "set", "returns-call"],
		["<root>/reify_case.py", 37, "scalar", "set", "returns-call"],
		["<root>/reify_case.py", 40, "passthrough", "set", "returns-call"],
	])]
	every c, _ in rf.not_reified {
		count(rf.deny) == 1 with input as {"case": c, "result": accept_all}
	}
}

test_unruled_case_is_withheld_not_admitted if {
	not rf.admitted with input as {"case": "382-reifies-reports-the-population-it-actually-read", "result": census}
	not rf.admitted with input as {"case": "383-an-unparseable-file-is-counted-as-skipped-never-silently-dro", "result": [[]]}
}
