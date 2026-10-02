# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed (W412): the reference's own rows are admitted, and each rule denies the defect it
# names. Rows are the ones the libcst-present replay returned (W390-peek.py key).
package pycodemod.key_test

import rego.v1

import data.pycodemod.key as ky

src_reads := [[["<root>/k.py", 4, "read", "project"], ["<root>/k.py", 5, "read", "project"], ["<root>/k.py", 6, "read", "project"]]]

test_reference_admitted if {
	ky.admitted with input as {"case": "122-key-finds-the-subscript-the-get-and-the-in-test", "result": src_reads}
	ky.admitted with input as {"case": "123-key-reports-the-enclosing-function-as-context", "result": src_reads}
	ky.admitted with input as {"case": "124-a-key-named-in-a-docstring-is-not-a-read", "result": [[]]}
	ky.admitted with input as {"case": "125-a-literal-in-a-schema-tuple-is-a-decl-not-a-read", "result": [[["<root>/k.py", 2, "decl", "<module>"], ["<root>/k.py", 8, "read", "project"]]]}
	ky.admitted with input as {"case": "126-a-declared-but-never-read-field-is-visible-as-decl-with-no-r", "result": [[["<root>/k.py", 2, "decl", "<module>"]]]}
}

# a subscript-only reader, at module context
test_subscript_only_denied if {
	sub := [[["<root>/k.py", 4, "read", "<module>"]]]
	count(ky.deny) == 1 with input as {"case": "122-key-finds-the-subscript-the-get-and-the-in-test", "result": sub}
	count(ky.deny) == 1 with input as {"case": "123-key-reports-the-enclosing-function-as-context", "result": sub}
}

# a grep reader: the docstring line is a read
test_grep_denied if {
	count(ky.deny) == 1 with input as {"case": "124-a-key-named-in-a-docstring-is-not-a-read", "result": [[["<root>/k.py", 1, "read", "<module>"]]]}
}

# decl folded into read
test_decl_folded_denied if {
	count(ky.deny) == 1 with input as {"case": "125-a-literal-in-a-schema-tuple-is-a-decl-not-a-read", "result": [[["<root>/k.py", 2, "read", "<module>"], ["<root>/k.py", 8, "read", "project"]]]}
	count(ky.deny) == 1 with input as {"case": "126-a-declared-but-never-read-field-is-visible-as-decl-with-no-r", "result": [[["<root>/k.py", 2, "read", "<module>"]]]}
}

test_unruled_case_is_withheld_not_admitted if {
	not ky.admitted with input as {"case": "121-not-a-key-case", "result": src_reads}
}
