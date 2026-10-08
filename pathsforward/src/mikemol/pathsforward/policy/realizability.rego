# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W850 (W848): the realizability charter's four gates over ONE waypoint, as a coordinate and a
# residue ledger. Never a bare reject: the verdict says how far a waypoint has got and, for every
# gate it has not closed, what is missing and what would close it.
#
# ⚑⚑ FORM AND OBSERVED FACTS ONLY, NEVER TRUTH. The policy reads what the waypoint DECLARES and
# the facts it is handed. An absent field is "not declared", which is residue, never clean.
#
# ⚑ ONE FILE, TWO READERS (agreed with nemik:W228 and luthen-observability:W666, 2026-10-08):
#   data.realizability.verdict   input = one item               -> one verdict
#   data.realizability.verdicts  input = {"items": [item, ...]} -> verdicts, in input order
# An item is {ref, waypoint, graph: {live, landed, known, enables}, facts, now}; every key but
# waypoint is optional. A verdict is {ref, level, reference_arm, residue: [{gate, reference_arm,
# what, closes_by, closes_ref?}]}. level is none < constructible < reachable < observable <
# coverable: the deepest gate with every gate before it clean. coverable with an empty residue is
# the charter's runtime-valid.
#
# ⚑ DEFERRAL YES, WAIVER NO. A `deferred` entry is residue at its gate. A waypoint key that names
# a waiver is itself residue at constructible, so a waived waypoint reads `none`.
#
# ⚑ THE CLOCK IS INPUT (input.now, RFC 3339), so a verdict is a pure function of its input. A fact
# older than max_age_seconds (data.realizability_config, default 3600) or unreadable floors its
# gate (the fact's own `gate`, default observable) and is named in the residue.
package realizability

import rego.v1

gates := ["constructible", "reachable", "observable", "coverable"]

default_arm := "host:luthen"

operator_arm := "operator"

bundled_title := 150

default max_age_seconds := 3600

# ⚑ A NAMED PATH, NOT object.get(data, ...): reading the whole of `data` reads this package too,
# and opa refuses the rule as recursive through every verdict.
max_age_seconds := data.realizability_config.max_age_seconds

verdict := judge(input) if input.waypoint

verdicts := [judge(item) | some item in input.items]

judge(item) := {
	"ref": object.get(item, "ref", object.get(item.waypoint, "symbol", "")),
	"level": level(residue(item)),
	"reference_arm": arm(item.waypoint),
	"residue": [entry | some entry in residue(item)],
}

level(found) := "coverable" if count(found) == 0

level(found) := name if {
	count(found) > 0
	first := min({i | some e in found; some i, g in gates; g == e.gate})
	name := _below(first)
}

_below(0) := "none"

_below(i) := gates[i - 1] if i > 0

arm(wp) := wp.reference_arm if {
	is_string(wp.reference_arm)
	wp.reference_arm != ""
} else := default_arm

nonblank(x) if {
	is_string(x)
	trim_space(x) != ""
}

residue(item) := (((constructible(item) | reachable(item)) | observable(item)) | coverable(item)) | lapsed(item)

_entry(gate, item, what, closes_by) := {
	"gate": gate,
	"reference_arm": arm(item.waypoint),
	"what": what,
	"closes_by": closes_by,
}

_status(wp) := object.get(wp, "status", "")

# --- constructible: a finite recipe exists --------------------------------------------------

constructible(item) := {e |
	some key in object.keys(item.waypoint)
	contains(lower(key), "waive")
	e := _entry(
		"constructible", item,
		sprintf("field %q marks a gate waived", [key]),
		"remove the field and record a deferral (--deferred) instead",
	)
} | {e |
	_status(item.waypoint) != "done"
	not nonblank(object.get(item.waypoint, "next_bounded_step", ""))
	e := _entry("constructible", item, "no next_bounded_step", "state the next bounded step (--next)")
} | {e |
	count(object.get(item.waypoint, "title", "")) > bundled_title
	e := _entry(
		"constructible", item,
		sprintf("title is over %d characters (bundled steps)", [bundled_title]),
		"split it into waypoints joined by enables",
	)
}

# --- reachable: every edge resolves, no cycle, an operator ask states its command ----------

_symbol(x) if regex.match(`^([A-Za-z0-9][A-Za-z0-9._-]*:)?W[1-9][0-9]*$`, x)

_resolves(item, ref) if ref in object.get(item, ["graph", "live"], [])

_resolves(item, ref) if ref in object.get(item, ["graph", "landed"], [])

_resolves(item, ref) if ref in object.get(item, ["graph", "known"], [])

_operator_ask(x) if startswith(x, "operator: decide ")

_operator_ask(x) if startswith(x, "operator: act ")

reachable(item) := {e |
	some field in ["blocked_on", "enables"]
	some ref in object.get(item.waypoint, field, [])
	_symbol(ref)
	not _resolves(item, ref)
	e := _entry(
		"reachable", item,
		sprintf("%s %s resolves to no waypoint", [field, ref]),
		"fix the reference, or hand the graph the queue that holds it",
	)
} | {e |
	some ref in object.get(item.waypoint, "blocked_on", [])
	not _symbol(ref)
	not _operator_ask(ref)
	e := _entry(
		"reachable", item,
		sprintf("blocked_on %q names no waypoint and states no operator ask", [ref]),
		"cite <repo>:W<n>, or write 'operator: decide|act <the ask>'",
	)
} | {e |
	some ref in object.get(item.waypoint, "blocked_on", [])
	startswith(ref, "operator: act ")
	not nonblank(object.get(item.waypoint, "command", ""))
	e := {
		"gate": "reachable",
		"reference_arm": operator_arm,
		"what": "an operator act ask states no exact command",
		"closes_by": "set --command to the exact command the operator runs",
	}
} | {e |
	sym := object.get(item.waypoint, "symbol", "")
	edges := object.get(item, ["graph", "enables"], {})
	some next in object.get(edges, sym, [])
	sym in graph.reachable(edges, {next})
	e := _entry(
		"reachable", item,
		sprintf("%s is on an enables cycle through %s", [sym, next]),
		"name the weaker edge and cut it, recording why in evidence",
	)
}

# --- observable: a declared witness or recorded proof ----------------------------------------

observable(item) := {e |
	not nonblank(object.get(item.waypoint, "witness", ""))
	not nonblank(object.get(item.waypoint, "evidence", ""))
	e := _entry(
		"observable", item,
		"no witness and no evidence",
		"declare a witness query (--witness) or record the command whose output proves it",
	)
}

# --- coverable: the population is a finite named source --------------------------------------

coverable(item) := {e |
	not is_object(object.get(item.waypoint, "population", null))
	e := _entry("coverable", item, "no population declared", "--population SOURCE BOUND")
} | {e |
	pop := object.get(item.waypoint, "population", null)
	is_object(pop)
	not is_number(object.get(pop, "bound", null))
	e := _entry("coverable", item, "population is unbounded", "name a finite bound for its source")
}

# --- deferred gates and lapsed facts ----------------------------------------------------------

lapsed(item) := {e |
	some d in object.get(item.waypoint, "deferred", [])
	e := object.union(
		{"gate": d.gate, "reference_arm": d.reference_arm, "what": d.what, "closes_by": d.closes_by},
		{k: v | some k, v in d; k == "closes_ref"},
	)
} | {e |
	some name, fact in object.get(item, "facts", {})
	object.get(fact, "unreadable", false) == true
	e := _entry(
		object.get(fact, "gate", "observable"), item,
		sprintf("fact %s is unreadable", [name]),
		sprintf("re-read %s", [name]),
	)
} | {e |
	some name, fact in object.get(item, "facts", {})
	not object.get(fact, "unreadable", false) == true
	_stale(item, fact)
	e := _entry(
		object.get(fact, "gate", "observable"), item,
		sprintf("fact %s is stale (as_of %s)", [name, fact.as_of]),
		sprintf("re-read %s within %d s", [name, max_age_seconds]),
	)
}

_stale(item, _) if {
	not nonblank(object.get(item, "now", ""))
}

_stale(_, fact) if {
	not nonblank(object.get(fact, "as_of", ""))
}

_stale(item, fact) if {
	age := time.parse_rfc3339_ns(item.now) - time.parse_rfc3339_ns(fact.as_of)
	age > max_age_seconds * 1000000000
}
