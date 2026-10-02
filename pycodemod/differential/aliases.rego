# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W404: aliases (_pycodemod_selftest.py:1220-1278). Each rule states the origin's own check
# against the captured rows, read with libcst present (W347, W348).
#   aliases rows: [path, line, form, module, bound, scope]
# 138-140 read the local_only=False call (`_arows`); 142-143 read the local_only=True call
# (`_scoped`). The capture holds each case's latest call, which is the one each reads.
# Withheld, not ruled:
#   (141 needed the sibling fixture target.py (:1220) to read `target` as local; the W405 capture
#    snapshots a file operand's siblings, so 141 is now ruled.)
#   144 reads `_arows` (local_only=False), but its captured call is the later `_scoped` one
#       (sticky), which filters FROM-STAR out.
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.aliases

import rego.v1

rows := input.result[0]

deny contains "138: the import forms are not the ten the fixture spells" if {
	input.case == "138-every-import-form-is-classified-and-comments-strings-are-not"
	sort([row[2] | some row in rows]) != ["AS-MOD", "BARE", "BARE", "BARE", "FROM", "FROM", "FROM", "FROM-AS", "FROM-STAR", "RELATIVE"]
}

func_rows := sort([[row[2], row[5]] | some row in rows; row[5] == "func"])

# scope is a column, not an excuse: the two function-scoped rows land on opposite sides
deny contains "139: the function body does not carry one BARE and one FROM import" if {
	input.case == "139-a-function-body-carries-both-a-compliant-and-a-violating-imp"
	func_rows != [["BARE", "func"], ["FROM", "func"]]
}

# ALIAS_COMPLIANT is {BARE}: the func-scoped compliant rows are exactly the one BARE
deny contains "140: the func-scoped compliant rows are not exactly [BARE]" if {
	input.case == "140-the-func-scoped-bare-import-is-compliant"
	[r[0] | some r in func_rows; r[0] == "BARE"] != ["BARE"]
}

# the false zero: a scoped question must narrow which SITES are reported, never what counts as local
deny contains "141: target vanished from the single-file locality set" if {
	input.case == "141-a-single-file-scope-does-not-empty-the-locality-set-the-fals"
	sort({row[3] | some row in rows; row[3] == "target"}) != ["target"]
}

deny contains "142: a foreign module survives local_only" if {
	input.case == "142-and-os-typing-are-still-excluded-as-foreign"
	some row in rows
	row[3] in {"os", "typing"}
}

deny contains "143: the relative import is filtered out" if {
	input.case == "143-a-relative-import-is-local-by-construction-never-filtered-ou"
	not "RELATIVE" in {row[2] | some row in rows}
}

judged := {
	"138-every-import-form-is-classified-and-comments-strings-are-not",
	"139-a-function-body-carries-both-a-compliant-and-a-violating-imp",
	"140-the-func-scoped-bare-import-is-compliant",
	"141-a-single-file-scope-does-not-empty-the-locality-set-the-fals",
	"142-and-os-typing-are-still-excluded-as-foreign",
	"143-a-relative-import-is-local-by-construction-never-filtered-ou",
}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
