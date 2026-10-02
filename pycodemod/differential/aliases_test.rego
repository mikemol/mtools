# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed (W404): the reference's own rows are admitted, and each rule denies the defect it
# names. Rows are the ones the libcst-present replay returned (W390-peek.py aliases).
package pycodemod.aliases_test

import rego.v1

import data.pycodemod.aliases as al

arows := [[
	["<root>/aliasuser.py", 1, "BARE", "target", ["target"], "module"],
	["<root>/aliasuser.py", 2, "AS-MOD", "target", ["_t"], "module"],
	["<root>/aliasuser.py", 3, "FROM", "target", ["pub"], "module"],
	["<root>/aliasuser.py", 4, "FROM-AS", "target", ["pub as p2"], "module"],
	["<root>/aliasuser.py", 5, "FROM-STAR", "target", ["*"], "module"],
	["<root>/aliasuser.py", 6, "RELATIVE", ".", ["sibling"], "module"],
	["<root>/aliasuser.py", 7, "BARE", "os", ["os"], "module"],
	["<root>/aliasuser.py", 8, "FROM", "typing", ["Optional"], "module"],
	["<root>/aliasuser.py", 12, "BARE", "target", ["target"], "func"],
	["<root>/aliasuser.py", 13, "FROM", "target", ["deferred"], "func"],
]]

scoped := [[["<root>/aliasuser.py", 6, "RELATIVE", ".", ["sibling"], "module"]]]

arows_cases := [
	"138-every-import-form-is-classified-and-comments-strings-are-not",
	"139-a-function-body-carries-both-a-compliant-and-a-violating-imp",
	"140-the-func-scoped-bare-import-is-compliant",
]

scoped_cases := [
	"142-and-os-typing-are-still-excluded-as-foreign",
	"143-a-relative-import-is-local-by-construction-never-filtered-ou",
]

test_reference_admitted if {
	every c in arows_cases {
		al.admitted with input as {"case": c, "result": arows}
	}
	every c in scoped_cases {
		al.admitted with input as {"case": c, "result": scoped}
	}
}

# a text scan: the comment and string mentions read as imports, the func scope lost
test_text_scan_denied if {
	texty := [array.concat(
		[[r[0], r[1], r[2], r[3], r[4], "module"] | some r in arows[0]],
		[["<root>/aliasuser.py", 9, "FROM", "target", ["ghost"], "module"]],
	)]
	every c in arows_cases {
		count(al.deny) == 1 with input as {"case": c, "result": texty}
	}
}

# local_only that filters by name alone: foreign kept, relative dropped
test_name_filter_denied if {
	name_filtered := [[["<root>/aliasuser.py", 7, "BARE", "os", ["os"], "module"]]]
	every c in scoped_cases {
		count(al.deny) == 1 with input as {"case": c, "result": name_filtered}
	}
}

test_single_file_locality_admitted_and_the_false_zero_denied if {
	single := "141-a-single-file-scope-does-not-empty-the-locality-set-the-fals"
	with_target := [array.concat(scoped[0], [["<root>/aliasuser.py", 1, "BARE", "target", ["target"], "module"]])]
	al.admitted with input as {"case": single, "result": with_target}
	# the shipped false zero: locality derived from the paths passed in, so target reads foreign
	count(al.deny) == 1 with input as {"case": single, "result": scoped}
}

test_unruled_case_is_withheld_not_admitted if {
	not al.admitted with input as {"case": "144-a-star-import-is-a-syntax-node-not-a-string-literal", "result": arows}
}
