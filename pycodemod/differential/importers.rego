# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W415: importers (_pycodemod_selftest.py:1183-1206). Each rule states the origin's own check
# against the captured rows, read with libcst present (W347, W348).
#   importers rows: [path, line, form, bound_names]
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.importers

import rego.v1

rows := input.result[0]

# the names a `from` import takes that a star re-export would skip
priv_names := sort({n | some row in rows; startswith(row[2], "from"); some n in row[3]; startswith(n, "_")})

deny contains "134: the import sites are not exactly the three the fixture spells" if {
	input.case == "134-every-import-site-of-the-module-is-found-and-only-those"
	[[row[2], sort(row[3])] | some row in rows] != [["import", ["_alias"]], ["from", ["_priv", "pub"]], ["from", ["deep"]]]
}

# what beats grep: the comment and the string literal on lines 5-6 are not sites
deny contains "135: a comment or string mention is an import site" if {
	input.case == "135-a-module-named-in-a-comment-or-a-string-is-not-an-import-sit"
	count(rows) != 3
}

deny contains "136: the re-export hazard is not exactly [_priv]" if {
	input.case == "136-a-name-taken-by-from-is-the-re-export-hazard"
	priv_names != ["_priv"]
}

# a `_` local alias reaches nothing through a re-export surface
deny contains "137: the _alias import alias is counted as a re-export hazard" if {
	input.case == "137-and-a-prefixed-import-alias-is-not"
	"_alias" in priv_names
}

judged := {
	"134-every-import-site-of-the-module-is-found-and-only-those",
	"135-a-module-named-in-a-comment-or-a-string-is-not-an-import-sit",
	"136-a-name-taken-by-from-is-the-re-export-hazard",
	"137-and-a-prefixed-import-alias-is-not",
}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
