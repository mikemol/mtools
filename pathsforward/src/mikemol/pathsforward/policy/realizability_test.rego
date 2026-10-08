# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W850: a witness and a control for every gate of data.realizability. Each case starts from
# `clean`, which reaches runtime-valid, and breaks exactly one thing, so a case that passes for
# the wrong reason would also pass the control.
package realizability_test

import rego.v1

import data.realizability

clean := {
	"symbol": "W1",
	"title": "one bounded thing",
	"status": "ready",
	"blocked_on": [],
	"enables": ["W2"],
	"next_bounded_step": "run the one command",
	"evidence": "the command printed OK",
	"population": {"source": "the tracked files under src/", "bound": 12},
}

graph := {"live": ["W1", "W2"], "landed": ["W3"], "known": ["peer:W9"], "enables": {"W1": ["W2"]}}

item(wp) := {"ref": "repo:W1", "waypoint": wp, "graph": graph, "now": "2026-10-08T12:00:00Z"}

v(wp) := got if {
	got := realizability.verdict with input as item(wp)
}

gates_of(verdict) := {e.gate | some e in verdict.residue}

test_a_clean_waypoint_is_runtime_valid if {
	got := v(clean)
	got.level == "coverable"
	got.residue == []
	got.ref == "repo:W1"
	got.reference_arm == "host:luthen"
}

test_a_declared_reference_arm_types_the_verdict if {
	v(object.union(clean, {"reference_arm": "operator"})).reference_arm == "operator"
}

test_no_next_step_is_residue_at_constructible if {
	got := v(object.remove(clean, ["next_bounded_step"]))
	got.level == "none"
	gates_of(got) == {"constructible"}
}

test_a_done_waypoint_needs_no_next_step if {
	done := object.union(object.remove(clean, ["next_bounded_step"]), {"status": "done"})
	v(done).level == "coverable"
}

test_a_bundled_title_is_residue_at_constructible if {
	long := concat("", ["x" | some _ in numbers.range(1, 200)])
	v(object.union(clean, {"title": long})).level == "none"
}

test_a_waiver_field_floors_the_waypoint_at_none if {
	got := v(object.union(clean, {"coverable_waived": true}))
	got.level == "none"
	some e in got.residue
	contains(e.what, "coverable_waived")
}

test_an_unresolved_blocker_is_residue_at_reachable if {
	got := v(object.union(clean, {"blocked_on": ["W404"], "status": "blocked"}))
	got.level == "constructible"
	gates_of(got) == {"reachable"}
}

test_landed_live_and_known_references_all_resolve if {
	v(object.union(clean, {"blocked_on": ["W3", "peer:W9"], "enables": ["W2"]})).level == "coverable"
}

test_a_blocker_that_names_nothing_is_residue_at_reachable if {
	gates_of(v(object.union(clean, {"blocked_on": ["mikemol"]}))) == {"reachable"}
}

test_an_operator_act_ask_without_a_command_is_judged_against_the_operator if {
	got := v(object.union(clean, {"blocked_on": ["operator: act run the cutover"]}))
	got.level == "constructible"
	some e in got.residue
	e.reference_arm == "operator"
	e.gate == "reachable"
}

test_an_operator_act_ask_with_its_command_is_clean if {
	wp := object.union(clean, {"blocked_on": ["operator: act run the cutover"], "command": "mikemol-cutover --apply"})
	v(wp).level == "coverable"
}

test_an_enables_cycle_is_residue_at_reachable if {
	cyclic := object.union(item(clean), {"graph": object.union(graph, {"enables": {"W1": ["W2"], "W2": ["W1"]}})})
	got := realizability.verdict with input as cyclic
	gates_of(got) == {"reachable"}
}

test_no_witness_and_no_evidence_is_residue_at_observable if {
	got := v(object.remove(clean, ["evidence"]))
	got.level == "reachable"
	gates_of(got) == {"observable"}
}

test_a_witness_alone_is_observable if {
	v(object.union(object.remove(clean, ["evidence"]), {"witness": "input.ok == true"})).level == "coverable"
}

test_no_population_is_residue_at_coverable if {
	got := v(object.remove(clean, ["population"]))
	got.level == "observable"
	gates_of(got) == {"coverable"}
}

test_an_unbounded_population_is_residue_at_coverable if {
	v(object.union(clean, {"population": {"source": "all of them", "bound": null}})).level == "observable"
}

test_a_deferred_gate_is_residue_and_keeps_its_ref if {
	deferral := {"gate": "observable", "reference_arm": "host:luthen", "what": "no probe yet", "closes_by": "write the probe", "closes_ref": "peer:W9"}
	got := v(object.union(clean, {"deferred": [deferral]}))
	got.level == "reachable"
	got.residue == [deferral]
}

test_an_unreadable_fact_floors_its_gate if {
	it := object.union(item(clean), {"facts": {"md0_who": {"unreadable": true, "gate": "reachable"}}})
	got := realizability.verdict with input as it
	got.level == "constructible"
}

test_a_stale_fact_floors_its_default_gate if {
	it := object.union(item(clean), {"facts": {"md0_who": {"value": "QUIET", "as_of": "2026-10-08T10:00:00Z"}}})
	got := realizability.verdict with input as it
	got.level == "reachable"
}

test_a_fresh_fact_is_clean if {
	it := object.union(item(clean), {"facts": {"md0_who": {"value": "QUIET", "as_of": "2026-10-08T11:59:00Z"}}})
	got := realizability.verdict with input as it
	got.level == "coverable"
}

test_max_age_is_policy_data if {
	it := object.union(item(clean), {"facts": {"md0_who": {"value": "QUIET", "as_of": "2026-10-08T11:59:00Z"}}})
	got := realizability.verdict with input as it with data.realizability_config.max_age_seconds as 10
	got.level == "reachable"
}

test_a_fact_with_no_clock_is_stale if {
	it := object.remove(object.union(item(clean), {"facts": {"f": {"value": 1, "as_of": "2026-10-08T11:59:00Z"}}}), ["now"])
	got := realizability.verdict with input as it
	got.level == "reachable"
}

test_verdicts_keep_input_order_and_each_ref if {
	second := object.union(item(object.remove(clean, ["population"])), {"ref": "repo:W2"})
	got := realizability.verdicts with input as {"items": [item(clean), second]}
	[g.ref | some g in got] == ["repo:W1", "repo:W2"]
	[g.level | some g in got] == ["coverable", "observable"]
}
