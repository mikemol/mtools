# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two-armed (W401): the reference's own rows are admitted, and each rule denies the defect it
# names. Rows are the ones the libcst-present replay returned (W390-peek.py shape).
package pycodemod.shape_test

import rego.v1

import data.pycodemod.shape as sh

hits := [[["<root>/shape.py", 3, "x = foo(a) or None"]]]

all_hits := [[
	["<root>/shape.py", 1, "\"\"\"A docstring mentioning foo or None, which is PROSE.\"\"\""],
	["<root>/shape.py", 2, "# a comment mentioning foo or None too"],
	["<root>/shape.py", 3, "x = foo(a) or None"],
	["<root>/shape.py", 4, "y = 1  # foo or None in a trailing comment on a CODE line"],
]]

test_reference_admitted if {
	every c in ["190-shape-locates-the-code-site-by-line", "191-a-docstring-mention-is-not-a-site", "192-a-comment-mention-is-not-a-site"] {
		sh.admitted with input as {"case": c, "result": hits}
	}
	sh.admitted with input as {"case": "193-shape-all-includes-prose", "result": all_hits}
	sh.admitted with input as {"case": "194-a-code-line-with-a-trailing-comment-is-not-excluded", "result": [[all_hits[0][3]]]}
	sh.admitted with input as {"case": "195-a-anchored-pattern-finds-the-column-0-site", "result": [[["<root>/anchor.py", 1, "import os"]]]}
	sh.admitted with input as {"case": "196-a-anchored-pattern-excludes-the-indented-site", "result": [[["<root>/anchor.py", 3, "import sys"]]]}
	sh.admitted with input as {"case": "197-if-name-locates-the-entry-point", "result": [[["<root>/anchor.py", 4, "if __name__ == '__main__':"]]]}
	sh.admitted with input as {"case": "198-a-syntax-error-is-a-verdict-not-a-crash", "result": [[false, "parse failed: ParserSyntaxError"]]}
}

# a scan that cannot tell prose from code: every mention is a site
test_prose_as_site_denied if {
	every c in ["190-shape-locates-the-code-site-by-line", "191-a-docstring-mention-is-not-a-site", "192-a-comment-mention-is-not-a-site"] {
		count(sh.deny) == 1 with input as {"case": c, "result": all_hits}
	}
}

# a scan that cannot see prose, or drops a commented code line
test_blind_scan_denied if {
	count(sh.deny) == 1 with input as {"case": "193-shape-all-includes-prose", "result": hits}
	count(sh.deny) == 1 with input as {"case": "194-a-code-line-with-a-trailing-comment-is-not-excluded", "result": [[]]}
}

# the un-anchored pre-filter: a `^` pattern returns a confident zero
test_confident_zero_denied if {
	every c in ["195-a-anchored-pattern-finds-the-column-0-site", "196-a-anchored-pattern-excludes-the-indented-site", "197-if-name-locates-the-entry-point"] {
		count(sh.deny) == 1 with input as {"case": c, "result": [[]]}
	}
}

test_syntax_error_as_pass_denied if {
	count(sh.deny) == 1 with input as {"case": "198-a-syntax-error-is-a-verdict-not-a-crash", "result": [[true, ""]]}
}

test_unruled_case_is_withheld_not_admitted if {
	not sh.admitted with input as {"case": "189-not-a-shape-case", "result": hits}
}
