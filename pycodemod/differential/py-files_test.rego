# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed (W423): the reference's own rows are admitted, and each rule denies the defect it
# names. Rows are the ones the replay returned under the W189 capture with the W421 binder.
package pycodemod.py_files_test

import rego.v1

import data.pycodemod.py_files as pf

test_reference_admitted if {
	every c, _ in pf.expected {
		pf.admitted with input as {"case": c, "result": [["<root>/src/m.py"]]}
	}
}

# the pre-fix skip tuple: build-output trees admitted beside the one real def
test_generated_tree_admitted_denied if {
	inflated := [["<root>/bazel-bin/mutants/m.py", "<root>/bazel-out/k8-fastbuild/m.py", "<root>/src/m.py"]]
	every c, _ in pf.expected {
		count(pf.deny) == 1 with input as {"case": c, "result": inflated}
	}
}

# the live-corpus walk the W187 capture produced must never read as a pass
test_live_corpus_walk_denied if {
	walk := [["/home/mikemol/github/substrate/catalog/library/concepts.py"]]
	every c, _ in pf.expected {
		count(pf.deny) == 1 with input as {"case": c, "result": walk}
	}
}

test_explicit_generated_root_admitted_and_its_skip_denied if {
	explicit := "108-naming-a-generated-tree-explicitly-still-reaches-it"
	pf.admitted with input as {"case": explicit, "result": [["<root>/mutants/m.py"]]}
	# the skip applied to the requested root itself: the explicit tree answers nothing
	count(pf.deny) == 1 with input as {"case": explicit, "result": [[]]}
}

test_unruled_case_is_withheld_not_admitted if {
	not pf.admitted with input as {"case": "106-not-a-py-files-case", "result": [[]]}
}

# W193: the symlink case is withheld even when its replay returns exactly the source-only answer
test_symlink_case_is_withheld_not_admitted if {
	not pf.admitted with input as {"case": pf.no_symlinks, "result": [["<root>/src/m.py"]]}
	count(pf.withheld) == 1 with input as {"case": pf.no_symlinks, "result": [["<root>/src/m.py"]]}
}
