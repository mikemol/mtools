# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed (W414): the reference's own rows are admitted, and each rule denies the defect it
# names. Rows are the ones the libcst-present replay returned (W390-peek.py source).
package pycodemod.source_test

import rego.v1

import data.pycodemod.source as so

target := [[["<root>/src.py", 3, 5, "def target(x):\n    # ⚑ a comment inside the body\n    return x + 1"]]]

body_cases := [
	"118-source-returns-exactly-one-def-with-its-cst-extent",
	"119-source-returns-the-body-text-comments-included",
	"120-source-does-not-swallow-the-following-def",
]

test_reference_admitted if {
	every c in body_cases {
		so.admitted with input as {"case": c, "result": target}
	}
	so.admitted with input as {"case": "121-source-finds-a-class-as-well-as-a-function", "result": [[]]}
}

# a fixed 4-line window from the def: comments stripped, the next def swallowed
test_line_window_denied if {
	window := [[["<root>/src.py", 3, 6, "def target(x):\n    return x + 1\ndef after():"]]]
	every c in body_cases {
		count(so.deny) == 1 with input as {"case": c, "result": window}
	}
}

test_phantom_rows_denied if {
	count(so.deny) == 1 with input as {"case": "121-source-finds-a-class-as-well-as-a-function", "result": target}
}

test_unruled_case_is_withheld_not_admitted if {
	not so.admitted with input as {"case": "117-not-a-source-case", "result": target}
}
