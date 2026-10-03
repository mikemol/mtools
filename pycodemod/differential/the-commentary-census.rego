# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W213: pycodemod's commentary-census section (_pycodemod_selftest.py:1342-1597), one callee at a
# time. This file judges commentary_kinds (#161-#164). Every other case in the section is
# WITHHELD until its callee gets rules, so the differential line counts it as not admitted.
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.commentary_census

import rego.v1

kinds := input.result[0]

judged := {
	"161-a-mark-in-a-selftest-name-classifies-as-executable-not-prose",
	"162-a-comment-mark-classifies-as-comment",
	"163-and-a-module-docstring-mark-classifies-as-docstring",
	"164-a-file-that-will-not-tokenize-is-reported-as-unparsed",
	"183-an-unresolvable-baseline-reports-lost-empty",
	"184-and-says-so-by-reporting-a-zero-baseline-not-a-pass",
	"185-while-still-counting-what-is-there-now",
	"171-two-byte-identical-methods-share-a-deep-skeleton-the-dedent",
	"172-and-their-hole-count-is-0-not-none-identical-not-undecidable",
	"173-a-single-def-name-yields-no-row-absent-scored-zero",
	"174-a-row-carries-both-rungs-name-n-nskel-holes-labels-nspine-sp",
	"186-no-mode-derives-its-denominator-from-matched-rows",
	"187-no-mode-turns-an-empty-scope-into-the-whole-corpus",
	"157-every-operand-taking-flag-the-derivers-find-is-declared-in-t",
	"158-and-the-named-deriver-overfires-all-still-over-fire-no-stale",
	"159-the-declared-mode-census-is-stated-not-assumed",
	"175-the-stdlib-road-to-modes-gives-the-same-answer-as-the-cst-ro",
	"176-and-it-finds-a-real-number-of-modes-not-an-empty-dict",
	"177-roundtrip-is-derived-as-needing-a-cst",
	"178-size-is-not-it-is-ast-splitlines",
	"179-commentary-is-not-it-is-splitlines-only",
	"152-every-marked-line-is-counted-in-comments-and-docstrings-and-",
	"153-a-line-lost-across-a-split-is-visible-in-the-group-total",
	"168-a-short-mark-does-not-fire-inside-a-word-nb-in-unbalanced",
	"169-and-it-does-fire-as-its-own-token",
	"170-while-the-glyph-mark-still-matches-having-no-word-boundary",
	"181-and-the-group-total-is-preserved",
	"182-a-duplicated-marker-text-is-reported-as-multi-homed",
}

# W215: commentary_census returns [rows, texts, n]; a row is [path, marked, distinct] and
# texts maps each normalized marked line to its [path, line] sites (selftest:1340).
census_rows := input.result[0][0]

census_texts := input.result[0][1]

group_total := sum([row[1] | some row in census_rows])

# W216: the origin's own CLI table. 157/158 call [modes(), argopt_flags(),
# declared_operand_flags()]; the deriver's MEASURED over-fires are named, not declared,
# because declaring them would make `--commentary <path>` eat its own path (selftest:1397).
deriver_overfires := {"--commentary", "--discards", "--banner"}

derived := {f | some f, wants in input.result[0]; wants} | {f | some f in input.result[1]}

# collision_apex returns [[bucket, [row...]]...]; the origin keys rows by name (selftest:1511).
# The label paths are cwd-relative, so no rule here names a path: the checks count them.
apex := {row[0]: row | some bucket in input.result[0]; some row in bucket[1]}

# commentary_lost returns [lost, new, before, after] (_pycodemod_selftest.py:1573).
lost := input.result[0]

# #161 a mark inside a selftest NAME or a printed message is code, not prose
deny contains "161: the executable rows are not exactly one check( and one print(" if {
	input.case == "161-a-mark-in-a-selftest-name-classifies-as-executable-not-prose"
	sort([split(row[2], "(")[0] | some row in kinds.executable]) != ["check", "print"]
}

# #162 a comment mark is a comment
deny contains "162: not exactly one comment row" if {
	input.case == "162-a-comment-mark-classifies-as-comment"
	count(kinds.comment) != 1
}

# #163 a module docstring mark is a docstring
deny contains "163: not exactly one docstring row" if {
	input.case == "163-and-a-module-docstring-mark-classifies-as-docstring"
	count(kinds.docstring) != 1
}

# #164 an untokenizable file is reported, never dropped
deny contains "164: the untokenizable file is not the one unparsed row" if {
	input.case == "164-a-file-that-will-not-tokenize-is-reported-as-unparsed"
	count(kinds.unparsed) != 1
}

# W218: an unresolvable baseline must be VISIBLE, not a pass. An empty LOST list alone can't
# tell "every line survived" from "the ref named nothing", so the counts carry the difference.
deny contains "183: an unresolvable baseline does not report LOST empty" if {
	input.case == "183-an-unresolvable-baseline-reports-lost-empty"
	lost[0] != []
}

deny contains "184: an unresolvable baseline does not report a ZERO before-count" if {
	input.case == "184-and-says-so-by-reporting-a-zero-baseline-not-a-pass"
	lost[2] != 0
}

deny contains "185: the after-count is not the 4 marked lines there now" if {
	input.case == "185-while-still-counting-what-is-there-now"
	lost[3] != 4
}

# W217 (1) the dedent: two byte-identical methods are a deep match, not no-shared-skeleton
deny contains "171: handler does not carry exactly 2 deep-skeleton labels" if {
	input.case == "171-two-byte-identical-methods-share-a-deep-skeleton-the-dedent"
	count(object.get(apex, ["handler", 4], [])) != 2
}

deny contains "172: handler's hole count is not 0 (identical, not undecidable)" if {
	input.case == "172-and-their-hole-count-is-0-not-none-identical-not-undecidable"
	object.get(apex, ["handler", 3], null) != 0
}

# (2) a non-colliding name is absent, not zero-scored
deny contains "173: the single-def name solo has a row" if {
	input.case == "173-a-single-def-name-yields-no-row-absent-scored-zero"
	"solo" in object.keys(apex)
}

# (3) the row is seven-wide: (name, n, nskel, holes, labels, nspine, spine_shared)
deny contains "174: the handler row is not seven-wide" if {
	input.case == "174-a-row-carries-both-rungs-name-n-nskel-holes-labels-nspine-sp"
	count(object.get(apex, "handler", [])) != 7
}

# W220: the class-scan over the tool's own source (the fixture is pycodemod.py) finds no
# defective spelling. Empty is compliant HERE because the fixture carries the scanned file,
# and a live scan of the current file also found 0 rows (W220, a one-shot probe retired under
# W466; re-measure with differential/peek.py). The origin filters
# rows through _in_dispatch, a selftest-local helper, so the spec demands that no row remains.
deny contains "186: a row-derived file count remains in the tool's source" if {
	input.case == "186-no-mode-derives-its-denominator-from-matched-rows"
	input.result[0] != []
}

deny contains "187: a `py_files(...) or None` widening remains in the tool's source" if {
	input.case == "187-no-mode-turns-an-empty-scope-into-the-whole-corpus"
	input.result[0] != []
}

deny contains sprintf("157: derived operand flags not declared: %v", [undeclared]) if {
	input.case == "157-every-operand-taking-flag-the-derivers-find-is-declared-in-t"
	undeclared := (derived - {f | some f in input.result[2]}) - deriver_overfires
	count(undeclared) > 0
}

# the exemption is itself gated: one that stops over-firing must be deleted, not outlive its cause
deny contains sprintf("158: stale over-fire exemptions: %v", [stale]) if {
	input.case == "158-and-the-named-deriver-overfires-all-still-over-fire-no-stale"
	stale := deriver_overfires - derived
	count(stale) > 0
}

deny contains "159: modes() is not a stated mode census (an object)" if {
	input.case == "159-the-declared-mode-census-is-stated-not-assumed"
	not is_object(input.result[0])
}

# the stdlib road and the CST road to modes() agree
deny contains "175: _modes_ast and modes() disagree" if {
	input.case == "175-the-stdlib-road-to-modes-gives-the-same-answer-as-the-cst-ro"
	input.result[0] != input.result[1]
}

deny contains "176: _modes_ast finds 20 or fewer modes" if {
	input.case == "176-and-it-finds-a-real-number-of-modes-not-an-empty-dict"
	count(input.result[0]) <= 20
}

# the CST precondition is per-mode, not blanket
deny contains "177: --roundtrip is not derived as needing a CST" if {
	input.case == "177-roundtrip-is-derived-as-needing-a-cst"
	not "--roundtrip" in input.result[0]
}

deny contains "178: --size is derived as needing a CST" if {
	input.case == "178-size-is-not-it-is-ast-splitlines"
	"--size" in input.result[0]
}

deny contains "179: --commentary is derived as needing a CST" if {
	input.case == "179-commentary-is-not-it-is-splitlines-only"
	"--commentary" in input.result[0]
}

# marks in a comment, a docstring and a printed string are all counted
deny contains "152: the whole file does not count 4 marked lines" if {
	input.case == "152-every-marked-line-is-counted-in-comments-and-docstrings-and-"
	census_rows[0][1] != 4
}

# a line dropped ACROSS a split shows in the group total, which per-file roundtrip cannot see
deny contains "153: the split group does not total 3 (the dropped line is invisible)" if {
	input.case == "153-a-line-lost-across-a-split-is-visible-in-the-group-total"
	group_total != 3
}

# a short mark is a token, not a substring: NB must not fire inside UNBALANCED
deny contains "168: the NB mark does not count exactly 1 line" if {
	input.case == "168-a-short-mark-does-not-fire-inside-a-word-nb-in-unbalanced"
	census_rows[0][1] != 1
}

deny contains "169: the NB note is not among the census texts" if {
	input.case == "169-and-it-does-fire-as-its-own-token"
	not "NB this one IS a note" in object.keys(census_texts)
}

# the glyph has no word boundary, so anchoring it would match nothing
deny contains "170: the glyph mark does not count exactly 1 line" if {
	input.case == "170-while-the-glyph-mark-still-matches-having-no-word-boundary"
	census_rows[0][1] != 1
}

# a re-indented line is the same line
deny contains "181: the re-indented group does not total 4" if {
	input.case == "181-and-the-group-total-is-preserved"
	group_total != 4
}

# a copy is not a move: a text in two places is its own finding
deny contains "182: the duplicated FOUR text is not reported at 2 sites" if {
	input.case == "182-a-duplicated-marker-text-is-reported-as-multi-homed"
	count(object.get(census_texts, "⚑ FOUR — a note on the second def", [])) != 2
}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
