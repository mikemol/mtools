# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed (W407): the reference's own rows are admitted where the origin passes, the origin's
# own FAIL (225) is pinned as a denial, and each rule denies the defect it names. Rows are the
# ones the libcst-present replay returned (W390-peek.py state).
package pycodemod.state_test

import rego.v1

import data.pycodemod.state as st

census := [[[
	["<root>/a.py", "bad", 1, "accum", ["append"], "list"],
	["<root>/c.py", "_C", 1, "cache", ["[]="], "dict"],
	["<root>/k.py", "TABLE", 1, "const", [], "dict"],
], 3]]

live := [[[["<root>/split_upstream.py", "_SNAPPED", 15, "accum", ["append"], "list"]], 2]]

synthetic := [
	"220-a-dict-read-inside-a-function-is-a-cache",
	"221-an-accumulator-mutated-only-at-module-scope-is-not-a-cache",
	"222-an-unmutated-table-is-const-not-a-cache",
	"223-every-candidate-is-classified-none-silently-dropped",
	"224-the-file-denominator-is-the-scope-not-the-matches",
]

test_reference_admitted_where_the_origin_passes if {
	every c in synthetic {
		st.admitted with input as {"case": c, "result": census}
	}
	st.admitted with input as {"case": "226-the-snapped-once-flag-does-not", "result": live}
}

# the origin's one known FAIL, pinned from the reference side
test_origin_memo_fail_is_denied if {
	count(st.deny) == 1 with input as {"case": "225-a-live-hand-rolled-memo-classifies-as-a-cache", "result": live}
	st.admitted with input as {"case": "225-a-live-hand-rolled-memo-classifies-as-a-cache", "result": [[array.concat(live[0][0], [["<root>/split_census.py", "_DAG", 43, "cache", ["[]="], "dict"]]), 2]]}
}

# a predicate keyed on mutation alone: every mutated container is a cache
test_mutation_only_predicate_denied if {
	flooded := [[[[r[0], r[1], r[2], "cache", r[4], r[5]] | some r in census[0][0]], 3]]
	count(st.deny) == 1 with input as {"case": "221-an-accumulator-mutated-only-at-module-scope-is-not-a-cache", "result": flooded}
	count(st.deny) == 1 with input as {"case": "222-an-unmutated-table-is-const-not-a-cache", "result": flooded}
	count(st.deny) == 1 with input as {"case": "226-the-snapped-once-flag-does-not", "result": [[[["<root>/split_upstream.py", "_SNAPPED", 15, "cache", ["append"], "list"]], 2]]}
}

# a filter: only the matches are rows, and the denominator is the match count
test_filtered_census_denied if {
	filtered := [[[census[0][0][1]], 1]]
	count(st.deny) == 1 with input as {"case": "223-every-candidate-is-classified-none-silently-dropped", "result": filtered}
	count(st.deny) == 1 with input as {"case": "224-the-file-denominator-is-the-scope-not-the-matches", "result": filtered}
	count(st.deny) == 1 with input as {"case": "220-a-dict-read-inside-a-function-is-a-cache", "result": [[[census[0][0][0]], 1]]}
}

test_unruled_case_is_withheld_not_admitted if {
	not st.admitted with input as {"case": "219-not-a-state-case", "result": census}
}
