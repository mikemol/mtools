# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W411: crossings (_pycodemod_selftest.py:2040-2093). Each rule states the origin's own check
# against the captured rows, read with libcst present (W347, W348). crossings RETURNS A
# GENERATOR: the adapter serialized it by repr ("<generator object crossings at 0x...>") until
# W411 taught conftest.normal to materialize iterators.
#   crossings rows: [path, def, line, class, why]; the origin keys them by def
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.crossings

import rego.v1

rows := input.result[0]

by_def := {row[1]: [row[3], row[4]] | some row in rows}

expected := {
	# a comprehension counts, and `why` keeps the source's order (disk, deps), not sorted()
	"238-a-comprehension-counts-and-the-order-is-the-source-s": ["parse_tree", ["corpus", "disk, deps"]],
	# a worklist under `while` is an unfold, and must beat the for-scan over the same stack
	"239-a-while-driven-closure-is-an-unfold-not-a-plain-loop": ["reach", ["unfold", "seen"]],
	"240-iterating-a-container-is-derived-not-corpus": ["rows", ["derived", "out"]],
	# an instrument gap, not a licence
	"241-a-container-built-with-no-visible-bound-is-unattr": ["parse", ["unattr", "rec"]],
	# paydown shows as a row MOVING class, never vanishing
	"242-a-generator-is-reported-as-paid-not-omitted": ["walk_it", ["yields", "generator"]],
}

deny contains sprintf("%v: %v reads %v, not %v", [substring(input.case, 0, 3), want[0], object.get(by_def, want[0], null), want[1]]) if {
	want := expected[input.case]
	object.get(by_def, want[0], null) != want[1]
}

judged := {c | some c, _ in expected}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
