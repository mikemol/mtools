# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed (W411): the reference's own rows are admitted, and each rule denies the defect it
# names. Rows are the ones the libcst-present replay returned once conftest materialized the
# generator (W390-peek.py crossings).
package pycodemod.crossings_test

import rego.v1

import data.pycodemod.crossings as xg

rows := [
	["<root>/xing.py", "parse_tree", 2, "corpus", "disk, deps"],
	["<root>/xing.py", "reach", 9, "unfold", "seen"],
	["<root>/xing.py", "rows", 16, "derived", "out"],
	["<root>/xing.py", "parse", 22, "unattr", "rec"],
	["<root>/xing.py", "walk_it", 27, "yields", "generator"],
]

test_reference_admitted if {
	every c in xg.judged {
		xg.admitted with input as {"case": c, "result": [rows]}
	}
}

# the first cut's reading: sorted why, no unfold class, local for unattr, generators skipped
test_first_cut_denied if {
	first_cut := [[
		["<root>/xing.py", "parse_tree", 2, "corpus", "deps, disk"],
		["<root>/xing.py", "reach", 9, "derived", "seen"],
		["<root>/xing.py", "rows", 16, "corpus", "out"],
		["<root>/xing.py", "parse", 22, "local", "rec"],
	]]
	every c in xg.judged {
		count(xg.deny) == 1 with input as {"case": c, "result": first_cut}
	}
}

# the adapter's old repr of an unconsumed generator must never read as a pass
test_unmaterialized_generator_denied if {
	every c in xg.judged {
		count(xg.deny) == 1 with input as {"case": c, "result": ["<generator object crossings at 0x7f>"]}
	}
}

test_unruled_case_is_withheld_not_admitted if {
	not xg.admitted with input as {"case": "237-not-a-crossings-case", "result": [rows]}
}
