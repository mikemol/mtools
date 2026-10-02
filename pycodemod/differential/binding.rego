# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W397: bindings / rivals / _cached_defs (_pycodemod_selftest.py:1661-1734). Each rule states the
# origin's own check against the captured result, read with libcst present (W347, W348).
#   bindings rows:     [kind, scope.name, line, live_start, live_end]
#   rivals rows:       [path, line, verdict, callee, body_lines]
#   _cached_defs rows: [name, line, delegates]
# Withheld, not ruled:
#   212-215 judge the module constant _DERIVER (and hashes of it); no call returns it, so the
#           captured result is an unrelated earlier _cached_defs value (sticky).
#   216-219 judge _roots() over the LIVE origin tree (W189: live-tree readers are do-not-port or
#           need a pinned snapshot); the result is a fact about this machine, not a fixture.
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.binding

import rego.v1

judged := {
	"199-binding-finds-assignment-loop-target-and-parameter",
	"200-binding-reports-the-defining-line",
	"201-binding-scopes-a-parameter-to-its-own-function",
	"202-binding-sees-an-import-as-a-binding",
	"203-binding-on-an-unbound-name-is-empty-not-an-error",
	"204-binding-reports-a-syntax-error-as-a-verdict",
	"205-rivals-calls-a-one-line-wrapper-delegates",
	"206-rivals-names-the-callee-so-the-operator-can-read-it",
	"207-rivals-does-not-count-a-docstring-as-a-body",
	"208-rivals-calls-a-real-body-reimplements",
	"209-a-cached-parse-is-stable-when-content-is-unchanged",
	"210-the-parse-reports-delegation",
	"211-editing-a-file-changes-its-cached-answer",
}

rows := input.result[0]

deny contains "199: binding kinds are not [assign, assign, param]" if {
	input.case == "199-binding-finds-assignment-loop-target-and-parameter"
	sort([row[0] | some row in rows]) != ["assign", "assign", "param"]
}

deny contains "200: defining lines are not [3, 4, 6]" if {
	input.case == "200-binding-reports-the-defining-line"
	sort([row[2] | some row in rows]) != [3, 4, 6]
}

# the parameter's live range starts at its own function, not module top
deny contains "201: the parameter is not scoped to its own function" if {
	input.case == "201-binding-scopes-a-parameter-to-its-own-function"
	[row[3] | some row in rows; row[0] == "param"] != [6]
}

deny contains "202: the import is not the one binding of os" if {
	input.case == "202-binding-sees-an-import-as-a-binding"
	[row[0] | some row in rows] != ["import"]
}

deny contains "203: an unbound name is not empty" if {
	input.case == "203-binding-on-an-unbound-name-is-empty-not-an-error"
	rows != []
}

deny contains "204: a syntax error is not reported as a verdict row" if {
	input.case == "204-binding-reports-a-syntax-error-as-a-verdict"
	not syntax_verdict
}

syntax_verdict if rows[0][0] == "<syntax-error>"

deny contains "205: the wrapper's verdicts are not [DELEGATES]" if {
	input.case == "205-rivals-calls-a-one-line-wrapper-delegates"
	[row[2] | some row in rows] != ["DELEGATES"]
}

delegates := [row | some row in rows; row[2] == "DELEGATES"]

deny contains "206: the DELEGATES row does not name _auth" if {
	input.case == "206-rivals-names-the-callee-so-the-operator-can-read-it"
	[row[3] | some row in delegates] != ["_auth"]
}

deny contains "207: the docstring is counted as body" if {
	input.case == "207-rivals-does-not-count-a-docstring-as-a-body"
	[row[4] | some row in delegates] != [1]
}

deny contains "208: the real body's verdicts are not [REIMPLEMENTS]" if {
	input.case == "208-rivals-calls-a-real-body-reimplements"
	[row[2] | some row in rows] != ["REIMPLEMENTS"]
}

deny contains "209: the re-read parse differs from the first" if {
	input.case == "209-a-cached-parse-is-stable-when-content-is-unchanged"
	input.result[0] != input.result[1]
}

deny contains "210: the first parse does not report delegation" if {
	input.case == "210-the-parse-reports-delegation"
	not rows[0][2] == true
}

deny contains "211: the edited file still reads as delegating" if {
	input.case == "211-editing-a-file-changes-its-cached-answer"
	not rows[0][2] == false
}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
