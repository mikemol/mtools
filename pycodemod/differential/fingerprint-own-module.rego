# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W336: fingerprint-own-module (_pycodemod_fingerprint.py's selftest, origin lines 713-897).
# 36 cases; 29 are declared unmeasured in gen_cases.py (a method callee, or an operand the capture
# kept only as a repr: an AST node or a registry), so they never reach a rule. The seven below are
# judged. site_referents rows are [line, kind, class, function, text, referents]; the adapter
# writes the referent frozenset as a sorted list.
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.fingerprint_own_module

import rego.v1

judged := {
	"343-strict-false-the-default-returns-keys-and-swallows-the-remai",
	"352-remainder-cannot-rise-either",
	"358-an-over-long-token-is-dropped-shape-bound-both-sides",
	"360-a-for-site-carries-its-iterable-as-a-referent",
	"361-an-if-site-carries-the-column-string-as-a-referent",
	"362-the-if-site-also-carries-its-bound-names",
	"370-a-third-site-sharing-nothing-is-not-in-the-class",
}

rows_of(kind) := [row | some row in input.result[0]; row[1] == kind]

carries(kind, referent) if {
	some row in rows_of(kind)
	referent in row[5]
}

# decode(210, {2: core_id, 5: relpath}) with strict=False: the understood keys, no raise
deny contains "343: decode did not return exactly the understood keys" if {
	input.case == "343-strict-false-the-default-returns-keys-and-swallows-the-remai"
	input.result[0] != ["core_id", "relpath"]
}

# omega_against(7) then omega_against(105): the smaller remainder has no more prime factors
deny contains "352: omega of the remainder rose" if {
	input.case == "352-remainder-cannot-rise-either"
	input.result[0] > input.result[1]
}

deny contains "358: an over-long token produced parts" if {
	input.case == "358-an-over-long-token-is-dropped-shape-bound-both-sides"
	input.result[0] != []
}

deny contains "360: no for site carries rows" if {
	input.case == "360-a-for-site-carries-its-iterable-as-a-referent"
	not carries("for", "rows")
}

deny contains "361: no if site carries core_id" if {
	input.case == "361-an-if-site-carries-the-column-string-as-a-referent"
	not carries("if", "core_id")
}

deny contains sprintf("362: no if site carries %v", [name]) if {
	input.case == "362-the-if-site-also-carries-its-bound-names"
	some name in ["r", "lim"]
	not carries("if", name)
}

# fp_contains(11, 6): 6 does not divide 11, so the third site is not in the class
deny contains "370: a site sharing nothing was contained" if {
	input.case == "370-a-third-site-sharing-nothing-is-not-in-the-class"
	input.result[0] != false
}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
