# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed (W393, batch A): the reference's own rows are admitted, and each rule family denies
# the defect it names. Rows are the ones the libcst-present replay returned (W390-peek.py).
package pycodemod.rivals_test

import rego.v1

import data.pycodemod.rivals as rv

reimplements := [[["<root>/r1.py", 1, "REIMPLEMENTS", "", 2], ["<root>/r2.py", 1, "REIMPLEMENTS", "", 2]]]

t5_dead := [[["<root>/t5.py", "factory", 7], ["<root>/t5.py", "truly_dead", 11]]]

test_reference_admitted if {
	rv.admitted with input as {"case": "031-rivals-both-bodies-read-reimplements", "result": reimplements}
	rv.admitted with input as {"case": "033-a-name-in-a-docstring-comment-is-not-a-call", "result": [[]]}
	rv.admitted with input as {"case": "034-a-def-with-no-caller-is-reported-dead", "result": [[["<root>/t2.py", "g", 3]]]}
	rv.admitted with input as {"case": "041-a-callback-passed-in-a-list-is-not-dead-the-otlp-shape", "result": t5_dead}
	rv.admitted with input as {"case": "045-a-def-that-is-neither-called-nor-referenced-is-still-dead", "result": t5_dead}
}

test_a_verdict_other_than_reimplements_denied if {
	bad := json.patch(reimplements, [{"op": "replace", "path": "/0/1/2", "value": "DISTINCT"}])
	count(rv.deny) == 1 with input as {"case": "031-rivals-both-bodies-read-reimplements", "result": bad}
}

test_a_comment_mention_reported_as_a_call_denied if {
	count(rv.deny) == 1 with input as {
		"case": "033-a-name-in-a-docstring-comment-is-not-a-call",
		"result": [[["<root>/t2.py", "call", "f", 1]]],
	}
}

test_a_wrong_dead_line_denied if {
	count(rv.deny) == 1 with input as {"case": "034-a-def-with-no-caller-is-reported-dead", "result": [[["<root>/t2.py", "g", 4]]]}
}

test_a_live_callback_reported_dead_denied if {
	bad := [[["<root>/t5.py", "hb_cb", 1], ["<root>/t5.py", "truly_dead", 11]]]
	count(rv.deny) == 1 with input as {"case": "041-a-callback-passed-in-a-list-is-not-dead-the-otlp-shape", "result": bad}
}

test_a_silenced_census_denied if {
	count(rv.deny) == 1 with input as {"case": "045-a-def-that-is-neither-called-nor-referenced-is-still-dead", "result": [[]]}
}

tq := [[["<root>/tq.py", 1, "thing", "def"], ["<root>/tq.py", 4, "thing", "ref"]]]

t5_scan := [[["<root>/t5.py", "def", "hb_cb", 1], ["<root>/t5.py", "ref", "hb_cb", 13]]]

test_batch_b_reference_admitted if {
	rv.admitted with input as {"case": "035-calls-is-blind-to-a-string-invoked-query-the-false-positive", "result": [[["<root>/tq.py", "def", "q_thing", 1]]]}
	rv.admitted with input as {"case": "036-sqlname-finds-the-q-prefixed-definition", "result": tq}
	rv.admitted with input as {"case": "037-and-the-string-reference-calls-cannot-see", "result": tq}
	rv.admitted with input as {"case": "038-sqlname-accepts-the-defined-spelling-too", "result": array.concat(tq, tq)}
	rv.admitted with input as {"case": "039-a-string-reference-is-reported-as-ref-not-call", "result": tq}
	rv.admitted with input as {"case": "040-a-query-defined-and-never-referenced-has-0-refs", "result": [[["<root>/tq2.py", 1, "unwired", "def"]]]}
	rv.admitted with input as {"case": "050-the-registrar-is-reached-as-a-value-by-each-decoration", "result": [[["<root>/t6.py", "def", "reg", 1], ["<root>/t6.py", "ref", "reg", 6]]]}
	rv.admitted with input as {"case": "064-ref-is-a-distinct-kind-not-folded-into-call", "result": t5_scan}
	rv.admitted with input as {"case": "065-the-value-use-is-recorded-as-a-ref-at-its-line", "result": t5_scan}
}

as_call := json.patch(tq, [{"op": "replace", "path": "/0/1/3", "value": "call"}])

test_batch_b_defects_denied if {
	count(rv.deny) == 1 with input as {"case": "035-calls-is-blind-to-a-string-invoked-query-the-false-positive", "result": [[["<root>/tq.py", "call", "q_thing", 4]]]}
	count(rv.deny) == 1 with input as {"case": "036-sqlname-finds-the-q-prefixed-definition", "result": [[["<root>/tq.py", 2, "thing", "def"]]]}
	count(rv.deny) == 1 with input as {"case": "037-and-the-string-reference-calls-cannot-see", "result": as_call}
	count(rv.deny) == 1 with input as {"case": "038-sqlname-accepts-the-defined-spelling-too", "result": [tq[0], []]}
	count(rv.deny) == 1 with input as {"case": "039-a-string-reference-is-reported-as-ref-not-call", "result": as_call}
	count(rv.deny) == 1 with input as {"case": "040-a-query-defined-and-never-referenced-has-0-refs", "result": tq}
	count(rv.deny) == 1 with input as {"case": "050-the-registrar-is-reached-as-a-value-by-each-decoration", "result": [[["<root>/t6.py", "def", "reg", 1]]]}
	count(rv.deny) == 1 with input as {"case": "064-ref-is-a-distinct-kind-not-folded-into-call", "result": [[["<root>/t5.py", "call", "hb_cb", 13]]]}
	count(rv.deny) == 1 with input as {"case": "065-the-value-use-is-recorded-as-a-ref-at-its-line", "result": [[["<root>/t5.py", "ref", "hb_cb", 12]]]}
}

test_batch_c_reference_admitted if {
	rv.admitted with input as {"case": "056-a-bare-prefix-with-no-suffix-is-not-a-framework-contract", "result": [null]}
	rv.admitted with input as {"case": "057-the-exemption-reports-which-contract-not-merely-that-there-i", "result": ["libcst/ast visitor — dispatched off the node type"]}
	rv.admitted with input as {"case": "058-ends-the-flags-a-later-token-is-not-seen-as-a-flag", "result": [["--literal"]]}
	rv.admitted with input as {"case": "059-and-is-delivered-as-an-operand-flag-shaped-and-all", "result": [["--selftest"]]}
	rv.admitted with input as {"case": "060-the-mode-before-is-still-recognised", "result": [["--literal"]]}
	rv.admitted with input as {"case": "061-with-no-every-token-remains-flag-visible", "result": [["--calls", "foo"]]}
	rv.admitted with input as {"case": "062-with-no-the-operand-tail-is-empty", "result": [[]]}
	rv.admitted with input as {"case": "063-a-at-argv-0-is-not-read-as-the-marker", "result": [["--calls", "foo"]]}
}

test_batch_c_defects_denied if {
	count(rv.deny) == 1 with input as {"case": "056-a-bare-prefix-with-no-suffix-is-not-a-framework-contract", "result": ["textual"]}
	count(rv.deny) == 1 with input as {"case": "057-the-exemption-reports-which-contract-not-merely-that-there-i", "result": [true]}
	count(rv.deny) == 1 with input as {"case": "058-ends-the-flags-a-later-token-is-not-seen-as-a-flag", "result": [["--literal", "--selftest"]]}
	count(rv.deny) == 1 with input as {"case": "059-and-is-delivered-as-an-operand-flag-shaped-and-all", "result": [[]]}
	count(rv.deny) == 1 with input as {"case": "060-the-mode-before-is-still-recognised", "result": [[]]}
	count(rv.deny) == 1 with input as {"case": "061-with-no-every-token-remains-flag-visible", "result": [["--calls"]]}
	count(rv.deny) == 1 with input as {"case": "062-with-no-the-operand-tail-is-empty", "result": [["foo"]]}
	count(rv.deny) == 1 with input as {"case": "063-a-at-argv-0-is-not-read-as-the-marker", "result": [[]]}
}

test_an_unruled_case_is_withheld_not_admitted if {
	not rv.admitted with input as {"case": "032-rivals-disjoint-signatures-are-distinguishable", "result": reimplements}
}
