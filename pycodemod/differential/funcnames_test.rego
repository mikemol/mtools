# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed (W403): the reference's own rows are admitted, and each rule denies the defect it
# names. Rows are the ones the libcst+sqlalchemy replay returned (W390-peek.py funcnames).
package pycodemod.funcnames_test

import rego.v1

import data.pycodemod.funcnames as fn

census := [[
	["<root>/func_case.py", 5, "portable", "coalesce", "generic"],
	["<root>/func_case.py", 5, "portable", "count", "generic"],
	["<root>/func_case.py", 5, "portable", "max", "generic"],
	["<root>/func_case.py", 8, "dialect_specific", "jsonb_agg", "verbatim"],
	["<root>/func_case.py", 8, "dialect_specific", "string_agg", "verbatim"],
	["<root>/func_case.py", 11, "sqlite_ism", "group_concat", "verbatim"],
]]

registry := [["aggregate_strings", "array_agg", "cast", "char_length", "coalesce", "concat", "count", "cube", "max", "min", "now", "sum"]]

test_reference_admitted if {
	every c, _ in fn.graded {
		fn.admitted with input as {"case": c, "result": census}
	}
	fn.admitted with input as {"case": "394-libcst-s-node-func-is-not-a-sqlalchemy-func-call", "result": census}
	fn.admitted with input as {"case": "395-the-generic-set-comes-from-sqlalchemy-s-own-registry-and-is-", "result": registry}
	fn.admitted with input as {"case": "396-a-core-only-file-still-has-no-literal-blockers-the-zero-was-", "result": [[]]}
}

# the grades inverted: a portable-vs-broken reading of the split
test_every_grade_denies_an_inversion if {
	inverted := [[[r[0], r[1], r[2], r[3], flip(r[4])] | some r in census[0]]]
	every c, _ in fn.graded {
		count(fn.deny) > 0 with input as {"case": c, "result": inverted}
	}
}

flip("generic") := "verbatim"

flip("verbatim") := "generic"

test_name_scoped_census_denied if {
	noisy := [array.concat(census[0], [["<root>/func_case.py", 14, "not_sqlalchemy", "value", "verbatim"]])]
	count(fn.deny) == 1 with input as {"case": "394-libcst-s-node-func-is-not-a-sqlalchemy-func-call", "result": noisy}
}

test_hardcoded_or_empty_registry_denied if {
	count(fn.deny) == 1 with input as {"case": "395-the-generic-set-comes-from-sqlalchemy-s-own-registry-and-is-", "result": [[]]}
	count(fn.deny) == 1 with input as {"case": "396-a-core-only-file-still-has-no-literal-blockers-the-zero-was-", "result": [[[5, "count"]]]}
}

test_unruled_case_is_withheld_not_admitted if {
	not fn.admitted with input as {"case": "397-but-the-core-built-sql-it-could-not-judge-is-now-recorded-no", "result": [[]]}
	not fn.admitted with input as {"case": "398-a-file-with-no-core-sql-clears-the-attribute-no-carry-over", "result": [[]]}
}
