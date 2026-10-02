# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed (W409): the reference's own rows are admitted, and each rule denies the defect it
# names. Rows are the ones the libcst-present replay returned (W390-peek.py literal).
package pycodemod.literal_test

import rego.v1

import data.pycodemod.literal as lt

sites := [
	["<root>/litfix.py", 1, "doc", "<module>", "A module about sqlite and how it is retired."],
	["<root>/litfix.py", 2, "decl", "<module>", "sqlite"],
	["<root>/litfix.py", 3, "other", "<module>", "sqlite"],
	["<root>/litfix.py", 7, "compare", "ph", "sqlite"],
	["<root>/litfix.py", 12, "arg", "go", "sqlite"],
]

captured := [[null, "ModuleNotFoundError: No module named 'psycopg'"], sites]

test_reference_admitted if {
	every c in lt.judged {
		lt.admitted with input as {"case": c, "result": captured}
	}
}

# every role folded into `other`: the undifferentiated list grep returns
test_folded_roles_denied if {
	folded := [captured[0], [[r[0], r[1], "other", r[3], r[4]] | some r in sites]]
	not_other := {c | some c, _ in lt.present} - {"236-a-plain-assignment-rhs-is-role-other"}
	every c in not_other {
		count(lt.deny) == 1 with input as {"case": c, "result": folded}
	}
	count(lt.deny) == 1 with input as {"case": "237-every-site-is-found-exactly-once-one-role-each", "result": folded}
}

# a role that climbs past its statement: the assignment RHS reads as the nearby compare
test_escaped_role_denied if {
	escaped := [captured[0], [[r[0], r[1], "compare", r[3], r[4]] | some r in sites; r[1] == 3]]
	count(lt.deny) == 1 with input as {"case": "236-a-plain-assignment-rhs-is-role-other", "result": escaped}
}

# a grep census: the comment line is a site
test_comment_as_site_denied if {
	grepped := [captured[0], array.concat(sites, [["<root>/litfix.py", 6, "other", "ph", "sqlite takes ? and psycopg takes %s"]])]
	count(lt.deny) == 1 with input as {"case": "235-a-mention-in-a-comment-is-not-a-literal-site", "result": grepped}
}

test_unruled_case_is_withheld_not_admitted if {
	not lt.admitted with input as {"case": "230-not-a-literal-case", "result": captured}
}
