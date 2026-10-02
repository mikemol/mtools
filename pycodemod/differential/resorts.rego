# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W226: resorts (_pycodemod_selftest.py:2900-2938). resorts(paths) returns rows
# [path, line, caller, callee, why]; the origin keys them by caller -> (callee, why).
# 388-390 read attributes resorts() stamps on itself, which the capture does not keep, so they
# are declared unmeasured in gen_cases.py and never reach a rule. Cost: one cold corpus walk per
# distinct fixture (~290s, W225), so run this with a 15-min budget.
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.resorts

import rego.v1

judged := {
	"384-sorting-a-callee-that-already-sorted-is-the-redundant-row",
	"385-a-re-keyed-sort-is-reported-separately-never-as-redundant",
	"386-reverse-counts-as-a-re-key-too",
	"387-sorting-a-callee-that-did-not-sort-is-not-a-re-sort-at-all",
}

by_caller := {row[2]: [row[3], row[4]] | some row in input.result[0]}

# sorted(upstream(xs)) pays twice for the same order
deny contains "384: redundant is not the (upstream, resort-of-sorted) row" if {
	input.case == "384-sorting-a-callee-that-already-sorted-is-the-redundant-row"
	object.get(by_caller, "redundant", null) != ["upstream", "resort-of-sorted"]
}

# a key= is a different order: reported, never counted as redundant
deny contains "385: rekeyed is not the (upstream, resort-rekeyed) row" if {
	input.case == "385-a-re-keyed-sort-is-reported-separately-never-as-redundant"
	object.get(by_caller, "rekeyed", null) != ["upstream", "resort-rekeyed"]
}

deny contains "386: reversed_too is not the (upstream, resort-rekeyed) row" if {
	input.case == "386-reverse-counts-as-a-re-key-too"
	object.get(by_caller, "reversed_too", null) != ["upstream", "resort-rekeyed"]
}

# plain() does not sort, so sorting its result is not a re-sort
deny contains "387: unrelated has a row" if {
	input.case == "387-sorting-a-callee-that-did-not-sort-is-not-a-re-sort-at-all"
	"unrelated" in object.keys(by_caller)
}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
