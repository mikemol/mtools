# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed (W419): the reference's own rows are admitted, and each rule denies the defect it
# names. Rows are the ones the libcst-present replay returned (W390-peek.py preamble).
package pycodemod.preamble_test

import rego.v1

import data.pycodemod.preamble as pr

scan := [[["<root>/t.py", "def", "f", 2], ["<root>/t.py", "call", "f", 7]]]

test_reference_admitted if {
	pr.admitted with input as {"case": "002-roundtrip-accepts-a-well-formed-file", "result": [[true, "identical"]]}
	every c, _ in pr.found {
		pr.admitted with input as {"case": c, "result": scan}
	}
}

# a transform that drops comments is not identical
test_lossy_roundtrip_denied if {
	count(pr.deny) == 1 with input as {"case": "002-roundtrip-accepts-a-well-formed-file", "result": [[false, "comments dropped"]]}
}

# a scan with the wrong line for each kind
test_misplaced_sites_denied if {
	shifted := [[["<root>/t.py", "def", "f", 1], ["<root>/t.py", "call", "f", 6]]]
	every c, _ in pr.found {
		count(pr.deny) == 1 with input as {"case": c, "result": shifted}
	}
}

test_declared_case_is_withheld_not_admitted if {
	not pr.admitted with input as {"case": "001-libcst-round-trips-comments-and-blank-lines", "result": []}
}
