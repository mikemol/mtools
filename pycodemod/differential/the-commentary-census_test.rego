# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Two arms per case: the reference output is admitted, and a mutation of it is denied.
package pycodemod.commentary_census_test

import rego.v1

import data.pycodemod.commentary_census as cc

good := [{
	"comment": [["<root>/kinds.py", 2, "⚑ TWO — a comment note"]],
	"docstring": [["<root>/kinds.py", 1, "⚑ ONE — a docstring note.\"\"\""]],
	"executable": [
		["<root>/kinds.py", 4, "check(\"⚑ THREE — a selftest name\", 1, 1)"],
		["<root>/kinds.py", 5, "print(\"  ⚑ FOUR — a message the program emits\")"],
	],
	"unparsed": [],
}]

broken := [{"comment": [], "docstring": [], "executable": [], "unparsed": [["<root>/broken.py", 1, "⚑ note"]]}]

test_reference_admitted if {
	every c in [
		"161-a-mark-in-a-selftest-name-classifies-as-executable-not-prose",
		"162-a-comment-mark-classifies-as-comment",
		"163-and-a-module-docstring-mark-classifies-as-docstring",
	] {
		cc.admitted with input as {"case": c, "result": good}
	}
	cc.admitted with input as {"case": "164-a-file-that-will-not-tokenize-is-reported-as-unparsed", "result": broken}
}

test_selftest_name_as_prose_denied if {
	bad := json.patch(good, [{"op": "remove", "path": "/0/executable/0"}])
	count(cc.deny) == 1 with input as {"case": "161-a-mark-in-a-selftest-name-classifies-as-executable-not-prose", "result": bad}
}

test_missing_comment_denied if {
	bad := json.patch(good, [{"op": "replace", "path": "/0/comment", "value": []}])
	count(cc.deny) == 1 with input as {"case": "162-a-comment-mark-classifies-as-comment", "result": bad}
}

test_doubled_docstring_denied if {
	bad := json.patch(good, [{"op": "add", "path": "/0/docstring/-", "value": ["<root>/kinds.py", 3, "x"]}])
	count(cc.deny) == 1 with input as {"case": "163-and-a-module-docstring-mark-classifies-as-docstring", "result": bad}
}

test_dropped_unparsed_denied if {
	bad := json.patch(broken, [{"op": "replace", "path": "/0/unparsed", "value": []}])
	count(cc.deny) == 1 with input as {"case": "164-a-file-that-will-not-tokenize-is-reported-as-unparsed", "result": bad}
}

test_unjudged_case_withheld if {
	not cc.admitted with input as {"case": "154-an-unjudged-case", "result": good}
}

texts := ["print(\" ⚑ THREE — a note the CLI prints\")", "⚑ FOUR — a note on the second def", "⚑ ONE — a note on the first def", "⚑ TWO — a note in a docstring.\"\"\""]

unresolved := [[[], texts, 0, 4]]

test_lost_reference_admitted if {
	every c in [
		"183-an-unresolvable-baseline-reports-lost-empty",
		"184-and-says-so-by-reporting-a-zero-baseline-not-a-pass",
		"185-while-still-counting-what-is-there-now",
	] {
		cc.admitted with input as {"case": c, "result": unresolved}
	}
}

test_phantom_loss_denied if {
	bad := json.patch(unresolved, [{"op": "replace", "path": "/0/0", "value": ["⚑ ONE — a note on the first def"]}])
	count(cc.deny) == 1 with input as {"case": "183-an-unresolvable-baseline-reports-lost-empty", "result": bad}
}

test_invented_baseline_denied if {
	bad := json.patch(unresolved, [{"op": "replace", "path": "/0/2", "value": 4}])
	count(cc.deny) == 1 with input as {"case": "184-and-says-so-by-reporting-a-zero-baseline-not-a-pass", "result": bad}
}

test_uncounted_present_denied if {
	bad := json.patch(unresolved, [{"op": "replace", "path": "/0/3", "value": 0}])
	count(cc.deny) == 1 with input as {"case": "185-while-still-counting-what-is-there-now", "result": bad}
}

apex_ref := [[["pairwise", [["handler", 2, 1, 0, ["../../..<root>/apexcase.py:2", "../../..<root>/apexcase.py:6"], 1, 2]]]]]

apex_cases := [
	"171-two-byte-identical-methods-share-a-deep-skeleton-the-dedent",
	"172-and-their-hole-count-is-0-not-none-identical-not-undecidable",
	"173-a-single-def-name-yields-no-row-absent-scored-zero",
	"174-a-row-carries-both-rungs-name-n-nskel-holes-labels-nspine-sp",
]

test_apex_reference_admitted if {
	every c in apex_cases {
		cc.admitted with input as {"case": c, "result": apex_ref}
	}
}

test_dropped_dedent_denied if {
	bad := json.patch(apex_ref, [{"op": "replace", "path": "/0/0/1/0/4", "value": []}])
	count(cc.deny) == 1 with input as {"case": apex_cases[0], "result": bad}
}

test_undecidable_holes_denied if {
	bad := json.patch(apex_ref, [{"op": "replace", "path": "/0/0/1/0/3", "value": null}])
	count(cc.deny) == 1 with input as {"case": apex_cases[1], "result": bad}
}

test_zero_scored_solo_denied if {
	bad := json.patch(apex_ref, [{"op": "add", "path": "/0/0/1/-", "value": ["solo", 1, 0, null, [], 0, 0]}])
	count(cc.deny) == 1 with input as {"case": apex_cases[2], "result": bad}
}

test_six_wide_row_denied if {
	bad := json.patch(apex_ref, [{"op": "remove", "path": "/0/0/1/0/6"}])
	count(cc.deny) == 1 with input as {"case": apex_cases[3], "result": bad}
}

test_clean_source_admitted if {
	every c in ["186-no-mode-derives-its-denominator-from-matched-rows", "187-no-mode-turns-an-empty-scope-into-the-whole-corpus"] {
		cc.admitted with input as {"case": c, "result": [[]]}
	}
}

test_row_derived_count_denied if {
	row := [[[120, "x = f\"{len({p for p, _ in rows})} file(s)\""]]]
	count(cc.deny) == 1 with input as {"case": "186-no-mode-derives-its-denominator-from-matched-rows", "result": row}
}

test_or_none_widening_denied if {
	row := [[[88, "rows = key_reads(name, py_files(*scope) or None)"]]]
	count(cc.deny) == 1 with input as {"case": "187-no-mode-turns-an-empty-scope-into-the-whole-corpus", "result": row}
}

table := [
	{"--commentary": true, "--discards": true, "--banner": true, "--calls": true, "--size": false},
	["--marks"],
	["--calls", "--marks"],
]

test_modes_reference_admitted if {
	every c in [
		"157-every-operand-taking-flag-the-derivers-find-is-declared-in-t",
		"158-and-the-named-deriver-overfires-all-still-over-fire-no-stale",
		"159-the-declared-mode-census-is-stated-not-assumed",
	] {
		cc.admitted with input as {"case": c, "result": table}
	}
}

test_undeclared_operand_flag_denied if {
	bad := json.patch(table, [{"op": "replace", "path": "/2", "value": ["--calls"]}])
	count(cc.deny) == 1 with input as {"case": "157-every-operand-taking-flag-the-derivers-find-is-declared-in-t", "result": bad}
}

test_stale_exemption_denied if {
	bad := json.patch(table, [{"op": "replace", "path": "/0/--banner", "value": false}])
	count(cc.deny) == 1 with input as {"case": "158-and-the-named-deriver-overfires-all-still-over-fire-no-stale", "result": bad}
}

test_no_census_denied if {
	count(cc.deny) == 1 with input as {"case": "159-the-declared-mode-census-is-stated-not-assumed", "result": [[]]}
}

many := {sprintf("--m%d", [n]): false | some n in numbers.range(1, 21)}

test_roads_agree_admitted if {
	cc.admitted with input as {"case": "175-the-stdlib-road-to-modes-gives-the-same-answer-as-the-cst-ro", "result": [many, many]}
	cc.admitted with input as {"case": "176-and-it-finds-a-real-number-of-modes-not-an-empty-dict", "result": [many]}
}

test_roads_disagree_denied if {
	count(cc.deny) == 1 with input as {"case": "175-the-stdlib-road-to-modes-gives-the-same-answer-as-the-cst-ro", "result": [many, {}]}
}

test_empty_road_denied if {
	count(cc.deny) == 1 with input as {"case": "176-and-it-finds-a-real-number-of-modes-not-an-empty-dict", "result": [{}]}
}

cst := [["--banner", "--roundtrip", "--touches"]]

test_cst_modes_admitted if {
	every c in [
		"177-roundtrip-is-derived-as-needing-a-cst",
		"178-size-is-not-it-is-ast-splitlines",
		"179-commentary-is-not-it-is-splitlines-only",
	] {
		cc.admitted with input as {"case": c, "result": cst}
	}
}

test_blanket_cst_denied if {
	blanket := [["--commentary", "--roundtrip", "--size"]]
	count(cc.deny) == 1 with input as {"case": "178-size-is-not-it-is-ast-splitlines", "result": blanket}
	count(cc.deny) == 1 with input as {"case": "179-commentary-is-not-it-is-splitlines-only", "result": blanket}
	count(cc.deny) == 1 with input as {"case": "177-roundtrip-is-derived-as-needing-a-cst", "result": [["--size"]]}
}

four := "⚑ FOUR — a note on the second def"

whole := [[[["<root>/whole.py", 4, 4]], {"⚑ ONE — a note on the first def": [["<root>/whole.py", 1]], four: [["<root>/whole.py", 6]]}, 4]]

split := [[[["<root>/left.py", 3, 3]], {"⚑ ONE — a note on the first def": [["<root>/left.py", 1]]}, 3]]

reind := [[[["<root>/left.py", 3, 3], ["<root>/reindented.py", 1, 1]], {four: [["<root>/reindented.py", 1]]}, 4]]

dup := [[[["<root>/whole.py", 4, 4], ["<root>/reindented.py", 1, 1]], {four: [["<root>/whole.py", 6], ["<root>/reindented.py", 1]]}, 5]]

nb := [[[["<root>/marks.py", 1, 1]], {"NB this one IS a note": [["<root>/marks.py", 2]]}, 1]]

test_census_reference_admitted if {
	cc.admitted with input as {"case": "152-every-marked-line-is-counted-in-comments-and-docstrings-and-", "result": whole}
	cc.admitted with input as {"case": "153-a-line-lost-across-a-split-is-visible-in-the-group-total", "result": split}
	cc.admitted with input as {"case": "168-a-short-mark-does-not-fire-inside-a-word-nb-in-unbalanced", "result": nb}
	cc.admitted with input as {"case": "169-and-it-does-fire-as-its-own-token", "result": nb}
	cc.admitted with input as {"case": "170-while-the-glyph-mark-still-matches-having-no-word-boundary", "result": nb}
	cc.admitted with input as {"case": "181-and-the-group-total-is-preserved", "result": reind}
	cc.admitted with input as {"case": "182-a-duplicated-marker-text-is-reported-as-multi-homed", "result": dup}
}

test_uncounted_docstring_denied if {
	bad := json.patch(whole, [{"op": "replace", "path": "/0/0/0/1", "value": 3}])
	count(cc.deny) == 1 with input as {"case": "152-every-marked-line-is-counted-in-comments-and-docstrings-and-", "result": bad}
}

test_invisible_loss_denied if {
	bad := json.patch(split, [{"op": "replace", "path": "/0/0/0/1", "value": 4}])
	count(cc.deny) == 1 with input as {"case": "153-a-line-lost-across-a-split-is-visible-in-the-group-total", "result": bad}
}

test_substring_mark_denied if {
	bad := json.patch(nb, [{"op": "replace", "path": "/0/0/0/1", "value": 2}])
	count(cc.deny) == 1 with input as {"case": "168-a-short-mark-does-not-fire-inside-a-word-nb-in-unbalanced", "result": bad}
}

test_missing_token_denied if {
	bad := json.patch(nb, [{"op": "replace", "path": "/0/1", "value": {}}])
	count(cc.deny) == 1 with input as {"case": "169-and-it-does-fire-as-its-own-token", "result": bad}
}

test_anchored_glyph_denied if {
	bad := json.patch(nb, [{"op": "replace", "path": "/0/0/0/1", "value": 0}])
	count(cc.deny) == 1 with input as {"case": "170-while-the-glyph-mark-still-matches-having-no-word-boundary", "result": bad}
}

test_reindent_as_loss_denied if {
	bad := json.patch(reind, [{"op": "replace", "path": "/0/0/1/1", "value": 0}])
	count(cc.deny) == 1 with input as {"case": "181-and-the-group-total-is-preserved", "result": bad}
}

test_copy_as_tie_denied if {
	bad := json.patch(dup, [{"op": "remove", "path": "/0/1/⚑ FOUR — a note on the second def/1"}])
	count(cc.deny) == 1 with input as {"case": "182-a-duplicated-marker-text-is-reported-as-multi-homed", "result": bad}
}
