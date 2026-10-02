# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed (W396): the reference's own rows are admitted, and each rule denies the defect it
# names. Rows are the ones the libcst-present replay returned (W390-peek.py values).
package pycodemod.values_test

import rego.v1

import data.pycodemod.values as vv

t6v_rows := [
	["<root>/t6v.py", 3, true, "<module>"],
	["<root>/t6v.py", 4, false, "<module>"],
	["<root>/t6v.py", 5, null, "<module>"],
	["<root>/t6v.py", 6, "UNKNOWN", "<module>"],
	["<root>/t6v.py", 7, "UNKNOWN", "<module>"],
	["<root>/t6v.py", 8, "UNKNOWN", "<module>"],
	["<root>/t6v.py", 10, "yes", "<module>"],
]

t6v := [[t6v_rows, 8]]

t6c := [[[["<root>/t6c.py", 2, true, "wrap"], ["<root>/t6c.py", 3, false, "<module>"]], 2]]

t6p := [[[["<root>/t6p.py", 1, "obs", "<module>"], ["<root>/t6p.py", 2, "edge", "<module>"], ["<root>/t6p.py", 3, "UNKNOWN", "<module>"]], 4]]

cg := [{"cga.leaf": ["sink"], "cga.mid": ["leaf"], "cga.other": ["run"], "cga.top": ["mid"], "cgb.run": ["sink"]}]

partition := [[
	[["<root>/t6v.py", 3], ["<root>/t6v.py", 4], ["<root>/t6v.py", 5], ["<root>/t6v.py", 10]],
	[["<root>/t6v.py", 6], ["<root>/t6v.py", 7], ["<root>/t6v.py", 8]],
]]

fwd := [[[["<root>/t4.py", 3]], [["<root>/t4.py", 4], ["<root>/t4.py", 5]]]]

t6v_cases := [
	"074-values-a-literal-true-is-reported-with-its-value",
	"075-values-a-literal-false-is-reported-with-its-value",
	"076-values-a-literal-none-is-a-value-not-the-unknown-marker",
	"077-values-a-literal-string-is-reported-with-its-value",
	"078-values-a-bare-name-is-unknown-never-guessed",
	"079-values-an-interpolated-f-string-is-unknown",
	"080-values-a-conditional-expression-is-unknown",
	"081-values-a-call-not-passing-the-keyword-is-not-a-row",
	"082-values-reports-n-of-m-over-the-call-population",
]

t6p_cases := [
	"085-values-ordinal-reads-the-positional-argument-at-that-index",
	"086-and-a-computed-positional-reports-unknown-rather-than-a-gues",
	"087-and-a-site-with-no-such-position-is-absent-not-unknown",
	"088-over-the-full-call-population-as-the-denominator",
	"089-and-a-decimal-string-selects-the-same-position-as-the-int",
]

test_reference_admitted if {
	every c in t6v_cases {
		vv.admitted with input as {"case": c, "result": t6v}
	}
	every c in t6p_cases {
		vv.admitted with input as {"case": c, "result": t6p}
	}
	vv.admitted with input as {"case": "083-values-a-call-inside-a-def-reports-that-def-as-its-context", "result": t6c}
	vv.admitted with input as {"case": "090-callgraph-attributes-calls-to-their-enclosing-def", "result": cg}
	vv.admitted with input as {"case": "091-which-calls-cannot-do-it-has-no-scope-tracking", "result": cg}
	vv.admitted with input as {"case": "092-reaches-follows-a-multi-hop-chain-within-a-module", "result": [{"sink": ["cga.top", "cga.mid", "cga.leaf", "sink"]}]}
	vv.admitted with input as {"case": "093-and-does-not-bridge-modules-on-a-shared-callee-spelling", "result": [{}]}
	vv.admitted with input as {"case": "094-a-target-beyond-the-depth-bound-is-absent-not-falsely-report", "result": [{}]}
	vv.admitted with input as {"case": "095-values-partitions-exactly-as-asserted-does", "result": partition}
	vv.admitted with input as {"case": "096-forwards-only-the-keyword-passing-call-counts-as-migrated", "result": fwd}
	vv.admitted with input as {"case": "097-forwards-positional-and-other-keyword-calls-are-missing", "result": fwd}
	vv.admitted with input as {"case": "103-an-unguarded-write-is-write-default", "result": [[true, "unguarded write at line 5"]]}
	vv.admitted with input as {"case": "104-an-apply-gated-write-is-not-write-default", "result": [[false, "gated on --apply"]]}
	vv.admitted with input as {"case": "105-writing-a-tempfile-is-not-write-default", "result": [[false, "writes only fixtures/tempfiles"]]}
	vv.admitted with input as {"case": "106-a-write-inside-selftest-is-not-a-write-path", "result": [[false, "writes only fixtures/tempfiles"]]}
}

# every literal guessed, every non-literal guessed: one value per line flipped
guessed := [[[[r[0], r[1], flip(r[2]), r[3]] | some r in t6v_rows], 8]]

flip(v) := "guess" if v == "UNKNOWN"

flip(v) := "UNKNOWN" if v != "UNKNOWN"

test_line_value_defects_denied if {
	every c in array.slice(t6v_cases, 0, 7) {
		count(vv.deny) == 1 with input as {"case": c, "result": guessed}
	}
}

test_none_collapsed_into_unknown_denied if {
	bad := json.patch(t6v, [{"op": "replace", "path": "/0/0/2/2", "value": "UNKNOWN"}])
	count(vv.deny) == 1 with input as {"case": "076-values-a-literal-none-is-a-value-not-the-unknown-marker", "result": bad}
}

test_shape_defects_denied if {
	extra := [[array.concat(t6v_rows, [["<root>/t6v.py", 9, false, "<module>"]]), 8]]
	count(vv.deny) == 1 with input as {"case": "081-values-a-call-not-passing-the-keyword-is-not-a-row", "result": extra}
	count(vv.deny) == 1 with input as {"case": "082-values-reports-n-of-m-over-the-call-population", "result": [[t6v_rows, 7]]}
	count(vv.deny) == 1 with input as {"case": "083-values-a-call-inside-a-def-reports-that-def-as-its-context", "result": [[[["<root>/t6c.py", 2, true, "wrap"], ["<root>/t6c.py", 3, false, "wrap"]], 2]]}
}

test_positional_defects_denied if {
	guess := json.patch(t6p, [{"op": "replace", "path": "/0/0/2/2", "value": "name"}])
	count(vv.deny) == 1 with input as {"case": "085-values-ordinal-reads-the-positional-argument-at-that-index", "result": guess}
	count(vv.deny) == 1 with input as {"case": "086-and-a-computed-positional-reports-unknown-rather-than-a-gues", "result": guess}
	kw := [[array.concat(t6p[0][0], [["<root>/t6p.py", 4, "UNKNOWN", "<module>"]]), 4]]
	count(vv.deny) == 1 with input as {"case": "087-and-a-site-with-no-such-position-is-absent-not-unknown", "result": kw}
	count(vv.deny) == 1 with input as {"case": "088-over-the-full-call-population-as-the-denominator", "result": [[t6p[0][0], 3]]}
	count(vv.deny) == 1 with input as {"case": "089-and-a-decimal-string-selects-the-same-position-as-the-int", "result": [[[], 4]]}
}

test_graph_defects_denied if {
	flat := [{"cga.leaf": ["sink"], "cga.mid": ["leaf", "sink"]}]
	count(vv.deny) == 1 with input as {"case": "090-callgraph-attributes-calls-to-their-enclosing-def", "result": flat}
	count(vv.deny) == 1 with input as {"case": "091-which-calls-cannot-do-it-has-no-scope-tracking", "result": flat}
	count(vv.deny) == 1 with input as {"case": "092-reaches-follows-a-multi-hop-chain-within-a-module", "result": [{}]}
	bridged := [{"sink": ["cga.other", "cgb.run", "sink"]}]
	count(vv.deny) == 1 with input as {"case": "093-and-does-not-bridge-modules-on-a-shared-callee-spelling", "result": bridged}
	count(vv.deny) == 1 with input as {"case": "094-a-target-beyond-the-depth-bound-is-absent-not-falsely-report", "result": bridged}
}

test_partition_and_forwards_defects_denied if {
	moved := [[partition[0][0], array.concat(partition[0][1], [["<root>/t6v.py", 5]])]]
	count(vv.deny) == 1 with input as {"case": "095-values-partitions-exactly-as-asserted-does", "result": moved}
	textual := [[[["<root>/t4.py", 1], ["<root>/t4.py", 3]], [["<root>/t4.py", 4]]]]
	count(vv.deny) == 1 with input as {"case": "096-forwards-only-the-keyword-passing-call-counts-as-migrated", "result": textual}
	count(vv.deny) == 1 with input as {"case": "097-forwards-positional-and-other-keyword-calls-are-missing", "result": textual}
}

test_write_default_defects_denied if {
	count(vv.deny) == 1 with input as {"case": "103-an-unguarded-write-is-write-default", "result": [[false, "x"]]}
	every c in ["104-an-apply-gated-write-is-not-write-default", "105-writing-a-tempfile-is-not-write-default", "106-a-write-inside-selftest-is-not-a-write-path"] {
		count(vv.deny) == 1 with input as {"case": c, "result": [[true, "x"]]}
	}
}

test_unruled_case_is_withheld_not_admitted if {
	not vv.admitted with input as {"case": "084-values-a-module-scope-fixture-call-reports-module", "result": t6c}
	not vv.admitted with input as {"case": "098-kwseen-does-not-leak-between-scans", "result": [true]}
}
