# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed (W402): the reference's own rows are admitted, and each rule denies the defect it
# names. Rows are the ones the libcst-present replay returned (W390-peek.py asserted).
package pycodemod.asserted_test

import rego.v1

import data.pycodemod.asserted as asr

split := [[
	[["<root>/t6.py", 3], ["<root>/t6.py", 5], ["<root>/t6.py", 9]],
	[["<root>/t6.py", 4], ["<root>/t6.py", 6], ["<root>/t6.py", 8]],
]]

test_reference_admitted if {
	every c in asr.judged {
		asr.admitted with input as {"case": c, "result": split}
	}
}

# the buckets swapped: every literal read as computed and the reverse
test_every_bucket_denies_a_swap if {
	swapped := [[split[0][1], split[0][0]]]
	every c, _ in asr.bucket {
		count(asr.deny) == 1 with input as {"case": c, "result": swapped}
	}
}

# the absent keyword folded into computed
test_absent_keyword_folded_denied if {
	folded := [[split[0][0], array.concat(split[0][1], [["<root>/t6.py", 7]])]]
	count(asr.deny) == 1 with input as {"case": "070-asserted-a-call-not-passing-the-keyword-is-in-neither-bucket", "result": folded}
}

test_unruled_case_is_withheld_not_admitted if {
	not asr.admitted with input as {"case": "073-asserted-splits-what-forwards-reports-as-one-bucket", "result": split}
}
