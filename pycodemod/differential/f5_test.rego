# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W420: the one arm a withheld-only spec owes: the sticky [[]] can never read as a pass.
package pycodemod.f5_test

import rego.v1

import data.pycodemod.f5

test_sticky_empty_is_withheld_not_admitted if {
	not f5.admitted with input as {"case": "133-every-dispatched-mode-appears-in-the-docstring", "result": [[]]}
	count(f5.withheld) == 1 with input as {"case": "133-every-dispatched-mode-appears-in-the-docstring", "result": [[]]}
}
