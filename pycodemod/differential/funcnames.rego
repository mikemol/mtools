# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W403: funcnames / _generic_func_names / portable_sites (_pycodemod_selftest.py:2945-3017).
# Each rule states the origin's own check against the captured result. Measured with libcst AND
# sqlalchemy present (w348-venv, sqlalchemy pinned to substrate's 2.0.51): without sqlalchemy
# every funcnames call raises ModuleNotFoundError, the same blindness class as W347's libcst.
#   funcnames rows: [path, line, ctx, name, grade]
#   _generic_func_names result: sorted names from SQLAlchemy's own registry
#   portable_sites result: literal blocker rows
# Withheld, not ruled:
#   397, 398 judge portable_sites.core_built, an attribute the function stamps on itself; the
#            capture never keeps it (the W226/W399 class).
#
# input = {case, fixture, operands, result}; result = [one value per origin call].
package pycodemod.funcnames

import rego.v1

rows := input.result[0]

# the origin keys by name; a name graded twice would collapse the same way
grade := {row[3]: row[4] | some row in rows}

graded := {
	"391-a-genericfunction-name-is-graded-generic-sqlalchemy-owns-the": {"count": "generic", "max": "generic", "coalesce": "generic"},
	# translated-vs-passed-through, never exists-vs-not: a valid postgres name is still verbatim
	"392-a-valid-but-dialect-specific-name-is-verbatim-not-an-error": {"string_agg": "verbatim", "jsonb_agg": "verbatim"},
	"393-the-sqlite-ism-that-made-a-capability-dark-is-in-the-verbati": {"group_concat": "verbatim"},
}

deny contains sprintf("%v: %v is graded %v, not %v", [substring(input.case, 0, 3), name, object.get(grade, name, null), want]) if {
	some name, want in graded[input.case]
	object.get(grade, name, null) != want
}

# receiver-scoped: libcst's node.func is an unrelated spelling
deny contains "394: libcst's node.func is reported as a SQLAlchemy func call" if {
	input.case == "394-libcst-s-node-func-is-not-a-sqlalchemy-func-call"
	some row in rows
	row[2] == "not_sqlalchemy"
}

# asked of the registry, never listed: the set is non-empty past a trivial size
deny contains "395: the generic set has 10 or fewer names" if {
	input.case == "395-the-generic-set-comes-from-sqlalchemy-s-own-registry-and-is-"
	count(rows) <= 10
}

deny contains "396: a Core-only file reports a literal blocker" if {
	input.case == "396-a-core-only-file-still-has-no-literal-blockers-the-zero-was-"
	rows != []
}

judged := {c | some c, _ in graded} | {
	"394-libcst-s-node-func-is-not-a-sqlalchemy-func-call",
	"395-the-generic-set-comes-from-sqlalchemy-s-own-registry-and-is-",
	"396-a-core-only-file-still-has-no-literal-blockers-the-zero-was-",
}

withheld contains sprintf("no rule yet for case %v", [input.case]) if {
	not input.case in judged
}

admitted if {
	count(deny) == 0
	count(withheld) == 0
}
