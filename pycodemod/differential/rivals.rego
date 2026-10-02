# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W340/W393: rivals, scan and dead (_pycodemod_selftest.py:400-580), batch A. Each rule states the
# origin's own check against the captured rows, read with libcst present (W347, W348): without it
# rivals/scan/dead return [] and the adapter refuses the run as OriginBlindError.
#   rivals rows: [path, line, verdict, _, n]   scan rows: [path, kind, name, line]
#   dead rows:   [path, name, line]
# 032 is withheld, not ruled: its origin check computes distinct SIGNATURES with its own ast walk,
# and the captured rivals() result does not carry them, so no rule over `result` measures it.
# Batches B (calls, sqlname, ref: W394) and C (exemption, argv: W395) are ruled.
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.rivals

import rego.v1

judged := {
	"031-rivals-both-bodies-read-reimplements",
	"033-a-name-in-a-docstring-comment-is-not-a-call",
	"034-a-def-with-no-caller-is-reported-dead",
	"035-calls-is-blind-to-a-string-invoked-query-the-false-positive",
	"036-sqlname-finds-the-q-prefixed-definition",
	"037-and-the-string-reference-calls-cannot-see",
	"038-sqlname-accepts-the-defined-spelling-too",
	"039-a-string-reference-is-reported-as-ref-not-call",
	"040-a-query-defined-and-never-referenced-has-0-refs",
	"041-a-callback-passed-in-a-list-is-not-dead-the-otlp-shape",
	"042-a-function-stored-in-a-registry-dict-is-not-dead",
	"043-a-closure-returned-by-a-factory-is-not-dead",
	"044-a-function-passed-as-key-is-not-dead",
	"045-a-def-that-is-neither-called-nor-referenced-is-still-dead",
	"046-a-bare-decorated-def-is-not-dead-reg-the-registry-shape",
	"047-a-called-decorator-def-is-not-dead-paramd-x",
	"048-a-dotted-decorator-def-is-not-dead-mod-attr",
	"049-an-undecorated-def-with-no-caller-is-still-dead",
	"050-the-registrar-is-reached-as-a-value-by-each-decoration",
	"051-a-libcst-visit-method-is-not-dead-framework-dispatched",
	"052-a-libcst-leave-method-is-not-dead",
	"053-a-textual-action-method-is-not-dead-binding-table-string",
	"054-a-textual-on-handler-is-not-dead-message-class-name",
	"055-an-ordinary-unused-method-in-the-same-class-is-still-dead",
	"056-a-bare-prefix-with-no-suffix-is-not-a-framework-contract",
	"057-the-exemption-reports-which-contract-not-merely-that-there-i",
	"058-ends-the-flags-a-later-token-is-not-seen-as-a-flag",
	"059-and-is-delivered-as-an-operand-flag-shaped-and-all",
	"060-the-mode-before-is-still-recognised",
	"061-with-no-every-token-remains-flag-visible",
	"062-with-no-the-operand-tail-is-empty",
	"063-a-at-argv-0-is-not-read-as-the-marker",
	"064-ref-is-a-distinct-kind-not-folded-into-call",
	"065-the-value-use-is-recorded-as-a-ref-at-its-line",
}

rows := input.result[0]

dead_names := {row[1] | some row in rows}

# rivals: both same-named bodies read REIMPLEMENTS
deny contains "031: the two verdicts are not both REIMPLEMENTS" if {
	input.case == "031-rivals-both-bodies-read-reimplements"
	sort([row[2] | some row in rows]) != ["REIMPLEMENTS", "REIMPLEMENTS"]
}

# no scan row is a `call`: a comment mention (033), a string-invoked query (035), a value use (064)
no_call := {
	"033-a-name-in-a-docstring-comment-is-not-a-call",
	"035-calls-is-blind-to-a-string-invoked-query-the-false-positive",
	"064-ref-is-a-distinct-kind-not-folded-into-call",
}

deny contains sprintf("%v: a scan row is reported as a call", [substring(input.case, 0, 3)]) if {
	input.case in no_call
	some row in rows
	row[1] == "call"
}

# sqlname rows: [path, line, name, kind]
sql_pairs(kind) := [[row[1], row[3]] | some row in rows; row[3] == kind]

deny contains "036: the q_ definition is not exactly [(1, def)]" if {
	input.case == "036-sqlname-finds-the-q-prefixed-definition"
	sql_pairs("def") != [[1, "def"]]
}

deny contains "037: the string reference is not exactly [(4, ref)]" if {
	input.case == "037-and-the-string-reference-calls-cannot-see"
	sql_pairs("ref") != [[4, "ref"]]
}

deny contains "038: the defined spelling resolves differently from the string spelling" if {
	input.case == "038-sqlname-accepts-the-defined-spelling-too"
	input.result[0] != input.result[1]
}

deny contains "039: the sqlname kinds are not exactly {def, ref}" if {
	input.case == "039-a-string-reference-is-reported-as-ref-not-call"
	{row[3] | some row in rows} != {"def", "ref"}
}

deny contains "040: an unreferenced query does not read [def] alone" if {
	input.case == "040-a-query-defined-and-never-referenced-has-0-refs"
	[row[3] | some row in rows] != ["def"]
}

# scan rows: [path, kind, name, line]
deny contains "050: the registrar is not reached as a value exactly once" if {
	input.case == "050-the-registrar-is-reached-as-a-value-by-each-decoration"
	count([row | some row in rows; row[1] == "ref"]) != 1
}

deny contains "065: the value use is not recorded as a ref at line 13" if {
	input.case == "065-the-value-use-is-recorded-as-a-ref-at-its-line"
	[row[3] | some row in rows; row[1] == "ref"] != [13]
}

# g is defined and never called
deny contains "034: dead is not exactly [(g, 3)]" if {
	input.case == "034-a-def-with-no-caller-is-reported-dead"
	[[row[1], row[2]] | some row in rows] != [["g", 3]]
}

# a value use keeps a def alive (callback list, registry dict, returned closure, key=)
live_by_value := {
	"041-a-callback-passed-in-a-list-is-not-dead-the-otlp-shape": "hb_cb",
	"042-a-function-stored-in-a-registry-dict-is-not-dead": "deco",
	"043-a-closure-returned-by-a-factory-is-not-dead": "inner",
	"044-a-function-passed-as-key-is-not-dead": "keyfn",
	"046-a-bare-decorated-def-is-not-dead-reg-the-registry-shape": "registered_bare",
	"047-a-called-decorator-def-is-not-dead-paramd-x": "registered_called",
	"048-a-dotted-decorator-def-is-not-dead-mod-attr": "registered_dotted",
	"051-a-libcst-visit-method-is-not-dead-framework-dispatched": "visit_Call",
	"052-a-libcst-leave-method-is-not-dead": "leave_FunctionDef",
	"053-a-textual-action-method-is-not-dead-binding-table-string": "action_reset",
	"054-a-textual-on-handler-is-not-dead-message-class-name": "on_mount",
}

deny contains sprintf("%v: %v is reported dead though it is live", [substring(input.case, 0, 3), name]) if {
	name := live_by_value[input.case]
	name in dead_names
}

# the anti-silencing guards: a def with no caller and no reference must STILL be reported
still_dead := {
	"045-a-def-that-is-neither-called-nor-referenced-is-still-dead": "truly_dead",
	"049-an-undecorated-def-with-no-caller-is-still-dead": "undecorated_dead",
	"055-an-ordinary-unused-method-in-the-same-class-is-still-dead": "helper_never_used",
}

deny contains sprintf("%v: %v is not reported dead; the census went silent", [substring(input.case, 0, 3), name]) if {
	name := still_dead[input.case]
	not name in dead_names
}

# framework_dispatch(name): None for no contract, else the contract's description
deny contains "056: a bare prefix is reported as a framework contract" if {
	input.case == "056-a-bare-prefix-with-no-suffix-is-not-a-framework-contract"
	input.result[0] != null
}

deny contains "057: the exemption does not name the libcst contract" if {
	input.case == "057-the-exemption-reports-which-contract-not-merely-that-there-i"
	not contains(sprintf("%v", [input.result[0]]), "libcst")
}

# flagged_argv / operand_tail: result[0] is the one call's list
deny contains "058: a token after -- is still seen as a flag" if {
	input.case == "058-ends-the-flags-a-later-token-is-not-seen-as-a-flag"
	"--selftest" in input.result[0]
}

argv_exact := {
	"059-and-is-delivered-as-an-operand-flag-shaped-and-all": ["--selftest"],
	"061-with-no-every-token-remains-flag-visible": ["--calls", "foo"],
	"062-with-no-the-operand-tail-is-empty": [],
	"063-a-at-argv-0-is-not-read-as-the-marker": ["--calls", "foo"],
}

deny contains sprintf("%v: argv split is %v, not %v", [substring(input.case, 0, 3), input.result[0], want]) if {
	want := argv_exact[input.case]
	input.result[0] != want
}

deny contains "060: the mode before -- is not recognised" if {
	input.case == "060-the-mode-before-is-still-recognised"
	not "--literal" in input.result[0]
}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
