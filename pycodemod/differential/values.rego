# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W396: values / callgraph / reaches / asserted / forwards / writes_by_default
# (_pycodemod_selftest.py:694-906). Each rule states the origin's own check against the captured
# result, read with libcst present (W347, W348).
#   values result:   [rows, total]; rows [path, line, value, context]; UNKNOWN arrives as the
#                    string "UNKNOWN" (the adapter's normal form), so a literal "UNKNOWN" would
#                    collide with it; no fixture here passes that literal.
#   asserted/forwards result: [first, second]; rows [path, line]
#   writes_by_default result: [verdict, reason]
# Withheld, not ruled:
#   084 judges the t6v call's contexts, but the capture attributes it to the later t6c call
#       (sticky), so `result` is not what the check reads.
#   098-102 are declared unmeasured in gen_cases.py (W222: module() and absent-callee buckets).
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.values

import rego.v1

judged := {
	"074-values-a-literal-true-is-reported-with-its-value",
	"075-values-a-literal-false-is-reported-with-its-value",
	"076-values-a-literal-none-is-a-value-not-the-unknown-marker",
	"077-values-a-literal-string-is-reported-with-its-value",
	"078-values-a-bare-name-is-unknown-never-guessed",
	"079-values-an-interpolated-f-string-is-unknown",
	"080-values-a-conditional-expression-is-unknown",
	"081-values-a-call-not-passing-the-keyword-is-not-a-row",
	"082-values-reports-n-of-m-over-the-call-population",
	"083-values-a-call-inside-a-def-reports-that-def-as-its-context",
	"085-values-ordinal-reads-the-positional-argument-at-that-index",
	"086-and-a-computed-positional-reports-unknown-rather-than-a-gues",
	"087-and-a-site-with-no-such-position-is-absent-not-unknown",
	"088-over-the-full-call-population-as-the-denominator",
	"089-and-a-decimal-string-selects-the-same-position-as-the-int",
	"090-callgraph-attributes-calls-to-their-enclosing-def",
	"091-which-calls-cannot-do-it-has-no-scope-tracking",
	"092-reaches-follows-a-multi-hop-chain-within-a-module",
	"093-and-does-not-bridge-modules-on-a-shared-callee-spelling",
	"094-a-target-beyond-the-depth-bound-is-absent-not-falsely-report",
	"095-values-partitions-exactly-as-asserted-does",
	"096-forwards-only-the-keyword-passing-call-counts-as-migrated",
	"097-forwards-positional-and-other-keyword-calls-are-missing",
	"103-an-unguarded-write-is-write-default",
	"104-an-apply-gated-write-is-not-write-default",
	"105-writing-a-tempfile-is-not-write-default",
	"106-a-write-inside-selftest-is-not-a-write-path",
}

unknown := "UNKNOWN"

out := input.result[0]

rows := out[0]

# values(q, reset): each line's value, as the origin reads _byline.get(line)
line_value := {
	"074-values-a-literal-true-is-reported-with-its-value": [3, true],
	"075-values-a-literal-false-is-reported-with-its-value": [4, false],
	"076-values-a-literal-none-is-a-value-not-the-unknown-marker": [5, null],
	"077-values-a-literal-string-is-reported-with-its-value": [10, "yes"],
	"078-values-a-bare-name-is-unknown-never-guessed": [6, unknown],
	"079-values-an-interpolated-f-string-is-unknown": [7, unknown],
	"080-values-a-conditional-expression-is-unknown": [8, unknown],
}

deny contains sprintf("%v: line %v does not read %v", [substring(input.case, 0, 3), want[0], want[1]]) if {
	want := line_value[input.case]
	not reads(want[0], want[1])
}

reads(line, value) if {
	some row in rows
	row[1] == line
	row[2] == value
}

deny contains "081: the call not passing the keyword is a row" if {
	input.case == "081-values-a-call-not-passing-the-keyword-is-not-a-row"
	some row in rows
	row[1] == 9
}

deny contains "082: values is not 7 of 8" if {
	input.case == "082-values-reports-n-of-m-over-the-call-population"
	[count(rows), out[1]] != [7, 8]
}

deny contains "083: contexts are not [(2, wrap), (3, <module>)]" if {
	input.case == "083-values-a-call-inside-a-def-reports-that-def-as-its-context"
	[[row[1], row[3]] | some row in rows] != [[2, "wrap"], [3, "<module>"]]
}

# values(up, 1): the positional reading
known_values := sort([row[2] | some row in rows; row[2] != unknown])

deny contains "085: the known positional values are not [edge, obs]" if {
	input.case == "085-values-ordinal-reads-the-positional-argument-at-that-index"
	known_values != ["edge", "obs"]
}

deny contains "086: the computed positional is not exactly one UNKNOWN" if {
	input.case == "086-and-a-computed-positional-reports-unknown-rather-than-a-gues"
	count([row | some row in rows; row[2] == unknown]) != 1
}

deny contains "087: a site with no such position is a row" if {
	input.case == "087-and-a-site-with-no-such-position-is-absent-not-unknown"
	count(rows) != 3
}

deny contains "088: the denominator is not the call population of 4" if {
	input.case == "088-over-the-full-call-population-as-the-denominator"
	out[1] != 4
}

# the int reading is pinned by 085-087; the string spelling must give the same rows
deny contains "089: the decimal string does not select position 1" if {
	input.case == "089-and-a-decimal-string-selects-the-same-position-as-the-int"
	[[row[1], row[2]] | some row in rows] != [[1, "obs"], [2, "edge"], [3, unknown]]
}

# callgraph: {caller: [callees]}
deny contains "090: cga.mid does not call exactly [leaf]" if {
	input.case == "090-callgraph-attributes-calls-to-their-enclosing-def"
	sort(object.get(out, "cga.mid", [])) != ["leaf"]
}

deny contains "091: the graph lacks a scoped caller" if {
	input.case == "091-which-calls-cannot-do-it-has-no-scope-tracking"
	some caller in ["cga.top", "cga.leaf"]
	not out[caller]
}

# reaches: {target: path}
deny contains "092: the multi-hop chain to sink is not followed" if {
	input.case == "092-reaches-follows-a-multi-hop-chain-within-a-module"
	object.get(out, "sink", null) != ["cga.top", "cga.mid", "cga.leaf", "sink"]
}

empty_reach := {
	"093-and-does-not-bridge-modules-on-a-shared-callee-spelling",
	"094-a-target-beyond-the-depth-bound-is-absent-not-falsely-report",
}

deny contains sprintf("%v: a path is reported where none may be", [substring(input.case, 0, 3)]) if {
	input.case in empty_reach
	out != {}
}

# asserted(q, reset): [literal sites, computed sites]; the partition 074-080 measures
deny contains "095: asserted's partition differs from values'" if {
	input.case == "095-values-partitions-exactly-as-asserted-does"
	[{row[1] | some row in out[0]}, {row[1] | some row in out[1]}] != [{3, 4, 5, 10}, {6, 7, 8}]
}

# forwards(r, quiet): [has, lacks]
deny contains "096: the migrated lines are not exactly [3]" if {
	input.case == "096-forwards-only-the-keyword-passing-call-counts-as-migrated"
	[row[1] | some row in out[0]] != [3]
}

deny contains "097: the missing lines are not exactly [4, 5]" if {
	input.case == "097-forwards-positional-and-other-keyword-calls-are-missing"
	[row[1] | some row in out[1]] != [4, 5]
}

# writes_by_default: [verdict, reason]
write_default := {
	"103-an-unguarded-write-is-write-default": true,
	"104-an-apply-gated-write-is-not-write-default": false,
	"105-writing-a-tempfile-is-not-write-default": false,
	"106-a-write-inside-selftest-is-not-a-write-path": false,
}

deny contains sprintf("%v: write-default is not %v", [substring(input.case, 0, 3), want]) if {
	want := write_default[input.case]
	out[0] != want
}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
