# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed: the reference-shaped result is admitted, and each defect is denied by its own rule.
package pycodemod.resorts_test

import rego.v1

import data.pycodemod.resorts as rs

rows := [
	["<root>/resort_case.py", 6, "redundant", "upstream", "resort-of-sorted"],
	["<root>/resort_case.py", 9, "rekeyed", "upstream", "resort-rekeyed"],
	["<root>/resort_case.py", 12, "reversed_too", "upstream", "resort-rekeyed"],
]

good := [rows]

test_reference_admitted if {
	rs.admitted with input as {"case": "384-sorting-a-callee-that-already-sorted-is-the-redundant-row", "result": good}
	rs.admitted with input as {"case": "385-a-re-keyed-sort-is-reported-separately-never-as-redundant", "result": good}
	rs.admitted with input as {"case": "386-reverse-counts-as-a-re-key-too", "result": good}
	rs.admitted with input as {"case": "387-sorting-a-callee-that-did-not-sort-is-not-a-re-sort-at-all", "result": good}
}

test_redundant_folded_into_rekey_denied if {
	bad := json.patch(good, [{"op": "replace", "path": "/0/0/4", "value": "resort-rekeyed"}])
	count(rs.deny) == 1 with input as {"case": "384-sorting-a-callee-that-already-sorted-is-the-redundant-row", "result": bad}
}

test_rekey_counted_redundant_denied if {
	bad := json.patch(good, [{"op": "replace", "path": "/0/1/4", "value": "resort-of-sorted"}])
	count(rs.deny) == 1 with input as {"case": "385-a-re-keyed-sort-is-reported-separately-never-as-redundant", "result": bad}
}

test_reverse_counted_redundant_denied if {
	bad := json.patch(good, [{"op": "replace", "path": "/0/2/4", "value": "resort-of-sorted"}])
	count(rs.deny) == 1 with input as {"case": "386-reverse-counts-as-a-re-key-too", "result": bad}
}

test_non_sorting_callee_reported_denied if {
	bad := [array.concat(rows, [["<root>/resort_case.py", 15, "unrelated", "plain", "resort-of-sorted"]])]
	count(rs.deny) == 1 with input as {"case": "387-sorting-a-callee-that-did-not-sort-is-not-a-re-sort-at-all", "result": bad}
}

test_unjudged_case_withheld if {
	not rs.admitted with input as {"case": "388-an-unjudged-case", "result": good}
}
