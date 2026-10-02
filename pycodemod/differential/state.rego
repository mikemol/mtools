# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W407: module_state (_pycodemod_selftest.py:1786-1846). Each rule states the origin's own check
# against the captured result, read with libcst present (W347, W348). The origin keys rows by
# name, so the rules do too.
#   result: [rows, n]; rows [path, name, line, class, mutators, type]
# ⚑ 225 is the origin's ONE known failure (W106: 407/408, row 225). The reference is expected to
# be DENIED here, faithfully: `_DAG` moved to an import site when split_pipeline was decomposed,
# and module_state declines to classify an import as a memo. A spec that admitted it would hide
# the origin's own red. 225/226 read live-tree files captured as fixture text (W189 class); the
# captured text is what the origin read, so they are measured, not withheld.
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.state

import rego.v1

rows := input.result[0][0]

class_of := {row[1]: row[3] | some row in rows}

classified := {
	"220-a-dict-read-inside-a-function-is-a-cache": ["_C", "cache"],
	# the discriminator: mutation alone would call both a cache; only the read-site differs
	"221-an-accumulator-mutated-only-at-module-scope-is-not-a-cache": ["bad", "accum"],
	"222-an-unmutated-table-is-const-not-a-cache": ["TABLE", "const"],
	"225-a-live-hand-rolled-memo-classifies-as-a-cache": ["_DAG", "cache"],
	"226-the-snapped-once-flag-does-not": ["_SNAPPED", "accum"],
}

deny contains sprintf("%v: %v classifies as %v, not %v", [substring(input.case, 0, 3), want[0], object.get(class_of, want[0], null), want[1]]) if {
	want := classified[input.case]
	object.get(class_of, want[0], null) != want[1]
}

# n of m over the whole population: set-aside rows are counted, not filtered
deny contains "223: not every candidate is classified" if {
	input.case == "223-every-candidate-is-classified-none-silently-dropped"
	count(rows) != 3
}

deny contains "224: the file denominator is not the scope of 3" if {
	input.case == "224-the-file-denominator-is-the-scope-not-the-matches"
	input.result[0][1] != 3
}

judged := {c | some c, _ in classified} | {
	"223-every-candidate-is-classified-none-silently-dropped",
	"224-the-file-denominator-is-the-scope-not-the-matches",
}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
