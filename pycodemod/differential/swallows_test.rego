# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed (W410): the reference's own row is admitted, and the rule denies the over-fire it
# names. The row is the one the libcst-present replay returned (W390-peek.py swallows).
package pycodemod.swallows_test

import rego.v1

import data.pycodemod.swallows as sw

case := "014-swallows-a-name-built-above-and-consumed-inside-is-not-an-es"

test_reference_admitted if {
	sw.admitted with input as {"case": case, "result": [[["<root>/w.py", 6, "narrow", "pass", false]]]}
}

# membership instead of position: the upstream read counts as an escape
test_membership_escape_denied if {
	count(sw.deny) == 1 with input as {"case": case, "result": [[["<root>/w.py", 6, "narrow", "pass", true]]]}
}

# the discard not found at all is not a pass either
test_missing_discard_denied if {
	count(sw.deny) == 1 with input as {"case": case, "result": [[]]}
}

test_declared_case_is_withheld_not_admitted if {
	not sw.admitted with input as {"case": "009-swallows-finds-all-three-discards", "result": [[]]}
}
