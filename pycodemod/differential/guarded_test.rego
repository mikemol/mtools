# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed (W498): the reference's own rows are admitted wherever the sides agree, and each rule
# denies the defect it names. ⚑ 008 is a PORT-FIX (W197): the reference's un-negated row is
# pinned as a DENIAL and the port's negated row as admitted, so a change on either side shows.
package pycodemod.guarded_test

import rego.v1

import data.pycodemod.guarded as gd

# the rows the reference replay returned (peek.py guarded)
reference := [[
	[["<root>/g.py", 4, ["apply"]], ["<root>/g.py", 7, ["a", "b"]], ["<root>/g.py", 11, ["c"]]],
	[["<root>/g.py", 2]],
]]

port := json.patch(reference, [{"op": "replace", "path": "/0/0/2/2", "value": ["not (c)"]}])

agreeing := gd.judged - {"008-guarded-else-body-over-reported-under-its-if-never-negated"}

test_reference_admitted_where_the_sides_agree if {
	every c in agreeing {
		gd.admitted with input as {"case": c, "result": reference}
	}
}

test_port_admitted_for_every_case if {
	every c in gd.judged {
		gd.admitted with input as {"case": c, "result": port}
	}
}

test_reference_else_body_denied if {
	count(gd.deny) == 1 with input as {"case": "008-guarded-else-body-over-reported-under-its-if-never-negated", "result": reference}
}

test_extra_top_row_denied if {
	bad := json.patch(reference, [{"op": "add", "path": "/0/1/-", "value": ["<root>/g.py", 4]}])
	count(gd.deny) == 1 with input as {"case": "005-guarded-an-unconditional-call-is-top", "result": bad}
}

test_missing_condition_denied if {
	bad := json.patch(reference, [{"op": "replace", "path": "/0/0/0/2", "value": []}])
	count(gd.deny) == 1 with input as {"case": "006-guarded-a-call-under-if-carries-its-test", "result": bad}
}

test_inner_first_order_denied if {
	bad := json.patch(reference, [{"op": "replace", "path": "/0/0/1/2", "value": ["b", "a"]}])
	count(gd.deny) == 1 with input as {"case": "007-guarded-nested-conditions-are-outermost-first", "result": bad}
}

# an empty result reports no row: undefined reads must not admit
test_empty_result_denied if {
	every c in gd.judged {
		not gd.admitted with input as {"case": c, "result": [[[], []]]}
	}
}

test_unruled_case_is_withheld_not_admitted if {
	not gd.admitted with input as {"case": "004-not-a-guarded-case", "result": reference}
	count(gd.withheld) == 1 with input as {"case": "004-not-a-guarded-case", "result": reference}
}
