# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W420: F5, "every dispatched mode appears in the docstring" (_pycodemod_selftest.py:1161-1173).
# NOT RULED, by reading the check: it calls no pycodemod mode. It regex-scans the origin's OWN
# `_dispatch` source for `"--flag" in argv` / `a == "--flag"` and compares against the module's
# `__doc__`. The captured result ([[]]) is a sticky attribution to an earlier, unrelated call, so
# a rule over it would judge the wrong value. The property is a driver concern (the origin's mode
# table, W127's "driver concern" class); the port owes its own docstring-vs-dispatch check, which
# is a port test, not a differential row.
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.f5

import rego.v1

judged := set()

withheld contains sprintf("no rule for case %v: the check reads the origin's own source, no call (sticky)", [input.case]) if {
	not input.case in judged
}

deny := set()

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
