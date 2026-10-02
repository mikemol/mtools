# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed (W397): the reference's own rows are admitted, and each rule denies the defect it
# names. Rows are the ones the libcst-present replay returned (W390-peek.py binding).
package pycodemod.binding_test

import rego.v1

import data.pycodemod.binding as bd

total := [[["assign", "outer.total", 3, 2, 5], ["assign", "outer.total", 4, 2, 5], ["param", "inner.total", 6, 6, 7]]]

wrapper := [[["<root>/riv.py", 1, "DELEGATES", "_auth", 1]]]

parsed := [[["f", 1, true]], [["f", 1, true]]]

total_cases := [
	"199-binding-finds-assignment-loop-target-and-parameter",
	"200-binding-reports-the-defining-line",
	"201-binding-scopes-a-parameter-to-its-own-function",
]

wrapper_cases := [
	"205-rivals-calls-a-one-line-wrapper-delegates",
	"206-rivals-names-the-callee-so-the-operator-can-read-it",
	"207-rivals-does-not-count-a-docstring-as-a-body",
]

test_reference_admitted if {
	every c in total_cases {
		bd.admitted with input as {"case": c, "result": total}
	}
	every c in wrapper_cases {
		bd.admitted with input as {"case": c, "result": wrapper}
	}
	bd.admitted with input as {"case": "202-binding-sees-an-import-as-a-binding", "result": [[["import", "os", 1, 1, 7]]]}
	bd.admitted with input as {"case": "203-binding-on-an-unbound-name-is-empty-not-an-error", "result": [[]]}
	bd.admitted with input as {"case": "204-binding-reports-a-syntax-error-as-a-verdict", "result": [[["<syntax-error>", "invalid syntax (bad.py, line 1)", 0, 0, 0]]]}
	bd.admitted with input as {"case": "208-rivals-calls-a-real-body-reimplements", "result": [[["<root>/riv.py", 4, "REIMPLEMENTS", "", 3]]]}
	bd.admitted with input as {"case": "209-a-cached-parse-is-stable-when-content-is-unchanged", "result": parsed}
	bd.admitted with input as {"case": "210-the-parse-reports-delegation", "result": parsed}
	bd.admitted with input as {"case": "211-editing-a-file-changes-its-cached-answer", "result": [[["f", 1, false]]]}
}

test_binding_defects_denied if {
	# the loop target folded into the assignment, the parameter given module-top liveness
	folded := [[["assign", "outer.total", 3, 2, 5], ["param", "inner.total", 7, 1, 7]]]
	every c in total_cases {
		count(bd.deny) == 1 with input as {"case": c, "result": folded}
	}
	count(bd.deny) == 1 with input as {"case": "202-binding-sees-an-import-as-a-binding", "result": [[]]}
	count(bd.deny) == 1 with input as {"case": "203-binding-on-an-unbound-name-is-empty-not-an-error", "result": [[["assign", "nowhere", 1, 1, 1]]]}
	count(bd.deny) == 1 with input as {"case": "204-binding-reports-a-syntax-error-as-a-verdict", "result": [[]]}
}

test_rivals_defects_denied if {
	# the docstring counted as body: a wrapper misread as a reimplementation of 2 lines
	misread := [[["<root>/riv.py", 1, "REIMPLEMENTS", "", 2]]]
	every c in wrapper_cases {
		count(bd.deny) == 1 with input as {"case": c, "result": misread}
	}
	count(bd.deny) == 1 with input as {"case": "208-rivals-calls-a-real-body-reimplements", "result": [[["<root>/riv.py", 4, "DELEGATES", "walk", 1]]]}
}

test_cache_defects_denied if {
	count(bd.deny) == 1 with input as {"case": "209-a-cached-parse-is-stable-when-content-is-unchanged", "result": [[["f", 1, true]], [["f", 1, false]]]}
	count(bd.deny) == 1 with input as {"case": "210-the-parse-reports-delegation", "result": [[["f", 1, false]]]}
	count(bd.deny) == 1 with input as {"case": "211-editing-a-file-changes-its-cached-answer", "result": [[["f", 1, true]]]}
}

test_unruled_case_is_withheld_not_admitted if {
	not bd.admitted with input as {"case": "212-the-deriver-tag-names-the-library-and-the-schema", "result": [[["f", 1, false]]]}
	not bd.admitted with input as {"case": "216-the-corpus-discovers-catalog", "result": [["catalog"]]}
}
