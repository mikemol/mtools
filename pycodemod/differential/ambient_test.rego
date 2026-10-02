# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed (W400): the reference's own rows are admitted, and each rule denies the defect it
# names. Rows are the ones the libcst-present replay returned (W390-peek.py ambient).
package pycodemod.ambient_test

import rego.v1

import data.pycodemod.ambient as am

census := [[
	["<root>/amb.py", 8, "builtin:open", "SCOPED", "path", "scoped"],
	["<root>/amb.py", 10, "glob:glob", "REPO", "agda/Substrate/**/*.agda", "repo_relative"],
	["<root>/amb.py", 14, "proc:run", "REPO", "scratch/prune_imports.py", "rel_script"],
	["<root>/amb.py", 16, "os:listdir", "SCOPED", "src", "explicit_source"],
	["<root>/amb.py", 18, "chdir", "MUTATES", "os.chdir('agda')", "mutate"],
]]

test_reference_admitted if {
	every c in am.judged {
		am.admitted with input as {"case": c, "result": census}
	}
}

# a census that lists every filesystem call: anchored and PATH-resolved sites get rows
test_every_no_row_denies_a_listed_call if {
	listed := [array.concat(census[0], [
		["<root>/amb.py", 4, "os:exists", "UNKNOWN", "x.agda", "anchored"],
		["<root>/amb.py", 6, "os:abspath", "UNKNOWN", "__file__", "anchored_file"],
		["<root>/amb.py", 12, "proc:run", "REPO", "agda", "command"],
	])]
	every c, _ in am.no_row {
		count(am.deny) == 1 with input as {"case": c, "result": listed}
	}
}

# every verdict collapsed to UNKNOWN: a reader that files its own gap as the corpus's ambiguity
test_every_verdict_denies_a_collapse if {
	collapsed := [[[r[0], r[1], r[2], "UNKNOWN", r[4], r[5]] | some r in census[0]]]
	every c, _ in am.verdict {
		count(am.deny) == 1 with input as {"case": c, "result": collapsed}
	}
}

test_unruled_case_is_withheld_not_admitted if {
	not am.admitted with input as {"case": "407-the-reader-declares-what-it-cannot-see", "result": census}
	not am.admitted with input as {"case": "408-and-the-population-is-reported-so-a-zero-is-distinguishable", "result": census}
}
