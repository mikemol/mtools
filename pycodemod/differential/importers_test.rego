# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed (W415): the reference's own rows are admitted, and each rule denies the defect it
# names. Rows are the ones the libcst-present replay returned (W390-peek.py importers).
package pycodemod.importers_test

import rego.v1

import data.pycodemod.importers as im

sites := [[
	["<root>/consumer.py", 1, "import", ["_alias"]],
	["<root>/consumer.py", 2, "from", ["_priv", "pub"]],
	["<root>/consumer.py", 3, "from", ["deep"]],
]]

test_reference_admitted if {
	every c in im.judged {
		im.admitted with input as {"case": c, "result": sites}
	}
}

# a grep reader: the comment and string lines are sites too
test_grep_reader_denied if {
	grepped := [array.concat(sites[0], [
		["<root>/consumer.py", 5, "from", ["ghost"]],
		["<root>/consumer.py", 6, "from", ["ghost"]],
	])]
	count(im.deny) == 1 with input as {"case": "134-every-import-site-of-the-module-is-found-and-only-those", "result": grepped}
	count(im.deny) == 1 with input as {"case": "135-a-module-named-in-a-comment-or-a-string-is-not-an-import-sit", "result": grepped}
}

# the shipped false positive: a `_` alias read as a `from`-taken name
test_alias_as_hazard_denied if {
	aliased := [[["<root>/consumer.py", 1, "from", ["_alias"]], sites[0][1], sites[0][2]]]
	count(im.deny) == 1 with input as {"case": "136-a-name-taken-by-from-is-the-re-export-hazard", "result": aliased}
	count(im.deny) == 1 with input as {"case": "137-and-a-prefixed-import-alias-is-not", "result": aliased}
}

test_unruled_case_is_withheld_not_admitted if {
	not im.admitted with input as {"case": "133-not-an-importers-case", "result": sites}
}
