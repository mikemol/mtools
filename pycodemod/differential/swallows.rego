# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W410: swallows (_pycodemod_selftest.py:189-223). One case is measurable; 009-013 are declared
# unmeasured in gen_cases.py (W222, "callee not in module": their recorded callee is the selftest's
# local `case` helper, which resolves to nothing in _pycodemod_placement).
#   swallows rows: [path, line, breadth, handler, feeds_verdict]
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.swallows

import rego.v1

rows := input.result[0]

# the buildtime.py:35-44 shape: a name built ABOVE the try and consumed INSIDE it is an input,
# not an escape; only a read AFTER the try feeds a verdict
deny contains "014: a name consumed inside the try is reported as feeding a verdict" if {
	input.case == "014-swallows-a-name-built-above-and-consumed-inside-is-not-an-es"
	[row[4] | some row in rows] != [false]
}

judged := {"014-swallows-a-name-built-above-and-consumed-inside-is-not-an-es"}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
