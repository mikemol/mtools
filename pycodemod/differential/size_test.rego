# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed (W406): the reference's own rows are admitted, and each rule denies the defect it
# names. Rows are the ones the libcst-present replay returned (W390-peek.py size).
package pycodemod.size_test

import rego.v1

import data.pycodemod.size as sz

two := [[[["<root>/two_entries.py", 7, 1, 2, "2 __main__ guards at 2,6"]], 1]]

all_cmt := [[[["<root>/commented.py", 1, 0, 0, "", 100, 0, 501]], 1]]

test_reference_admitted if {
	sz.admitted with input as {"case": "145-two-main-guards-are-reported-at-any-size", "result": two}
	sz.admitted with input as {"case": "146-and-the-reason-names-them", "result": two}
	every c in sz.empty {
		sz.admitted with input as {"case": c, "result": [[[], 1]]}
	}
	every c, _ in sz.column {
		sz.admitted with input as {"case": c, "result": all_cmt}
	}
}

test_guard_defects_denied if {
	count(sz.deny) == 1 with input as {"case": "145-two-main-guards-are-reported-at-any-size", "result": [[[], 1]]}
	count(sz.deny) == 1 with input as {"case": "146-and-the-reason-names-them", "result": [[[["<root>/two_entries.py", 7, 1, 2, "too large"]], 1]]}
}

# W481: a port that reports NO row has not named the guards; an undefined rows[0] must not admit
test_no_row_does_not_name_the_guards if {
	count(sz.deny) == 1 with input as {"case": "146-and-the-reason-names-them", "result": [[[], 1]]}
	not sz.admitted with input as {"case": "146-and-the-reason-names-them", "result": [[[], 1]]}
}

test_flooded_census_denied if {
	every c in sz.empty {
		count(sz.deny) == 1 with input as {"case": c, "result": [[[["<root>/x.py", 501, 0, 0, "501 > 100"]], 1]]}
	}
}

# physical count INSERTED mid-row and counted as code: every positional read shifts
test_shifted_row_denied if {
	shifted := [[[["<root>/commented.py", 501, 0, 0, 501, "", 100, 0]], 1]]
	every c, _ in sz.column {
		count(sz.deny) == 1 with input as {"case": c, "result": shifted}
	}
}

test_unruled_case_is_withheld_not_admitted if {
	not sz.admitted with input as {"case": "144-not-a-size-case", "result": two}
}
