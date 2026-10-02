# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W398: reifies (_pycodemod_selftest.py:2822-2871). Each rule states the origin's own check
# against the captured rows, read with libcst present (W347, W348).
#   reifies rows: [path, line, name, kind, why]
# Withheld, not ruled:
#   382, 383 judge reifies.population and reifies.skipped, attributes the function stamps on
#            itself; the capture never keeps them (the class W226 declared for resorts 388-390,
#            not yet declared for these two in gen_cases.py's _FN_ATTRS).
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.reifies

import rego.v1

rows := input.result[0]

# name -> [kind, why]; the origin keys rows by name the same way
by_name := {row[2]: [row[3], row[4]] | some row in rows}

reified := {
	"371-a-returned-set-literal-is-a-set-reification": ["lit_set", ["set", "returns-literal"]],
	"372-a-returned-dict-literal-is-a-dict-reification": ["lit_dict", ["dict", "returns-literal"]],
	"373-a-returned-set-comprehension-counts-the-corpus-shaped-builde": ["comp_set", ["set", "returns-comp"]],
	"374-a-returned-dict-comprehension-counts": ["comp_dict", ["dict", "returns-comp"]],
	"375-return-set-xs-is-a-call-built-reification": ["call_set", ["set", "returns-call"]],
	# the row the mode exists for: a sort paid for and dropped must not fold into returns-call
	"376-return-sorted-xs-gets-its-own-why-not-returns-call": ["call_sorted", ["sorted", "returns-sorted"]],
	"377-a-name-grown-by-append-and-returned-is-an-accumulator": ["accum", ["accum", "returns-accum"]],
	"378-a-dict-grown-by-subscript-assign-and-returned-is-an-accumula": ["accum_dict", ["accum", "returns-accum"]],
}

deny contains sprintf("%v: %v does not read %v", [substring(input.case, 0, 3), want[0], want[1]]) if {
	want := reified[input.case]
	object.get(by_name, want[0], null) != want[1]
}

# the negative half that keeps the census honest
not_reified := {
	"379-a-generator-is-not-a-reification-it-is-the-target-shape": "streams",
	"380-a-returned-scalar-is-not-a-reification": "scalar",
	"381-returning-an-argument-unchanged-is-not-a-reification": "passthrough",
}

deny contains sprintf("%v: %v is reported as a reification", [substring(input.case, 0, 3), name]) if {
	name := not_reified[input.case]
	by_name[name]
}

judged := {c | some c, _ in reified} | {c | some c, _ in not_reified}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
