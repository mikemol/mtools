# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W423: py_files / _roots (_pycodemod_selftest.py:917-952), under the W189 capture (W418), whose
# varargs and `<global ROOT>` the adapter now replays (W421). The fixture is one temp tree with
# `m.py` under src/ and five generated or cache trees; only src/ is source.
#   result: [paths]; the adapter writes the fixture root as `<root>`
# 108 names `<tree>/bazel-bin` explicitly while its one captured file is bazel-bin/mutants/m.py;
# until W424 `rehome` rooted at bazel-bin/mutants and never rewrote the shallower operand, so the
# replay walked a vanished temp dir ([]). Rehome now widens the root to the operand.
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.py_files

import rego.v1

source_only := ["<root>/src/m.py"]

expected := {
	# a derived copy reads exactly like source; every generated/cache tree is skipped
	"107-py-files-skips-bazel-generated-cache-trees-keeping-only-sour": source_only,
	# the top-level case that bit: an unfiltered _roots() made bazel-bin its own root
	"109-roots-drops-generated-trees-that-are-top-level-entries": source_only,
	# a per-workspace bazel symlink cannot be enumerated by name, so it is dropped by prefix
	"110-a-bazel-workspace-convenience-symlink-is-dropped-by-prefix": source_only,
}

deny contains sprintf("%v: found %v, not %v", [substring(input.case, 0, 3), input.result[0], want]) if {
	want := expected[input.case]
	input.result[0] != want
}

# the skip is relative to the REQUESTED root: naming a generated tree explicitly still answers
deny contains sprintf("108: basenames are %v, not [m.py]", [names]) if {
	input.case == "108-naming-a-generated-tree-explicitly-still-reaches-it"
	names := [base | some p in input.result[0]; parts := split(p, "/"); base := parts[count(parts) - 1]]
	names != ["m.py"]
}

judged := {c | some c, _ in expected} | {"108-naming-a-generated-tree-explicitly-still-reaches-it"}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
