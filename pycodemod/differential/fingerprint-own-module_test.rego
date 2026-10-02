# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed: the reference result (W336-peek, replayed through substrate's
# _pycodemod_fingerprint) is admitted, and each defect is denied by its own rule.
package pycodemod.fingerprint_own_module_test

import rego.v1

import data.pycodemod.fingerprint_own_module as fo

sites := [[
	[2, "for", "unclassified", "f", "for r in rows", ["rows"]],
	[3, "and", "mode-branch", "f", "r['core_id'] and lim", ["core_id", "lim", "r"]],
	[3, "if", "mode-branch", "f", "r['core_id'] and lim", ["core_id", "lim", "r"]],
	[4, "return-in-loop", "early-exit", "f", "return r", ["core_id", "lim", "r"]],
]]

reference := {
	"343-strict-false-the-default-returns-keys-and-swallows-the-remai": [["core_id", "relpath"]],
	"352-remainder-cannot-rise-either": [1, 3],
	"358-an-over-long-token-is-dropped-shape-bound-both-sides": [[]],
	"360-a-for-site-carries-its-iterable-as-a-referent": sites,
	"361-an-if-site-carries-the-column-string-as-a-referent": sites,
	"362-the-if-site-also-carries-its-bound-names": sites,
	"370-a-third-site-sharing-nothing-is-not-in-the-class": [false],
}

test_reference_admitted if {
	every case, result in reference {
		fo.admitted with input as {"case": case, "result": result}
	}
}

test_every_judged_case_has_a_reference if {
	fo.judged == {case | some case, _ in reference}
}

test_remainder_swallowed_into_keys_denied if {
	count(fo.deny) == 1 with input as {"case": "343-strict-false-the-default-returns-keys-and-swallows-the-remai", "result": [["core_id", "relpath", "7"]]}
}

test_omega_rising_denied if {
	count(fo.deny) == 1 with input as {"case": "352-remainder-cannot-rise-either", "result": [3, 1]}
}

test_over_long_token_kept_denied if {
	count(fo.deny) == 1 with input as {"case": "358-an-over-long-token-is-dropped-shape-bound-both-sides", "result": [["zzzz"]]}
}

test_for_site_without_iterable_denied if {
	bad := json.patch(sites, [{"op": "replace", "path": "/0/0/5", "value": []}])
	count(fo.deny) == 1 with input as {"case": "360-a-for-site-carries-its-iterable-as-a-referent", "result": bad}
}

test_if_site_without_column_denied if {
	bad := json.patch(sites, [{"op": "replace", "path": "/0/2/5", "value": ["lim", "r"]}])
	count(fo.deny) == 1 with input as {"case": "361-an-if-site-carries-the-column-string-as-a-referent", "result": bad}
}

test_if_site_without_bound_names_denied if {
	bad := json.patch(sites, [{"op": "replace", "path": "/0/2/5", "value": ["core_id"]}])
	count(fo.deny) == 2 with input as {"case": "362-the-if-site-also-carries-its-bound-names", "result": bad}
}

test_unrelated_site_contained_denied if {
	count(fo.deny) == 1 with input as {"case": "370-a-third-site-sharing-nothing-is-not-in-the-class", "result": [true]}
}

test_unjudged_case_withheld if {
	not fo.admitted with input as {"case": "335-registry-accepts-any-non-empty-key-no-taxonomy", "result": [[]]}
}
