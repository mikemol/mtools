# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W409: literal_sites (_pycodemod_selftest.py:1950-2012). Each rule states the origin's own check
# against the captured result, read with libcst present (W347, W348).
#   literal_sites rows: [path, line, role, ctx, value]; the origin keys them as {(role, value)}
# The capture also holds an unrelated earlier call (pg_probe_status, which reads [null, error]
# without psycopg); the checks read the literal_sites call, which is the LAST one, so the rules
# read input.result[count - 1], never a fixed index that a re-capture could shift.
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.literal

import rego.v1

rows := input.result[count(input.result) - 1]

lit := {[row[2], row[4]] | some row in rows}

present := {
	# the dispatch branch a backend retirement deletes
	"231-a-comparison-operand-is-role-compare": ["compare", "sqlite"],
	# the caller naming the retired value, which survives the branch deletion
	"232-a-call-argument-is-role-arg": ["arg", "sqlite"],
	"233-a-collection-element-is-role-decl": ["decl", "sqlite"],
	"234-a-docstring-mention-is-role-doc-not-role-other": ["doc", "A module about sqlite and how it is retired."],
	# the role must stop at its own statement
	"236-a-plain-assignment-rhs-is-role-other": ["other", "sqlite"],
}

deny contains sprintf("%v: (%v, %v) is not a site", [substring(input.case, 0, 3), want[0], want[1]]) if {
	want := present[input.case]
	not want in lit
}

# the case that beats grep: the comment naming psycopg is not a site
deny contains "235: a comment mention is reported as a literal site" if {
	input.case == "235-a-mention-in-a-comment-is-not-a-literal-site"
	some pair in lit
	contains(pair[1], "psycopg")
}

# a total catches a role silently folded into its neighbour
deny contains "237: the sites are not exactly five distinct (role, value) pairs" if {
	input.case == "237-every-site-is-found-exactly-once-one-role-each"
	count(lit) != 5
}

judged := {c | some c, _ in present} | {
	"235-a-mention-in-a-comment-is-not-a-literal-site",
	"237-every-site-is-found-exactly-once-one-role-each",
}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
