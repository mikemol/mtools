# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W231: the operator's standing rules, enforced at PreToolUse. Input is the harness's hook payload
# ({tool_name, tool_input, cwd, ...}). Every deny names its standing-rule number, and a rule
# enforced here is removed from the loop's prompt (operator ruling 2026-09-28).
package mtools.hook

import rego.v1

command := input.tool_input.command if input.tool_name == "Bash"

# W236: the command with every quoted span removed; flag rules match the words the shell will
# run, not text a command merely carries (a note, a message, a pattern).
unquoted := regex.replace(command, `"[^"]*"|'[^']*'`, " ")

edited := input.tool_input.file_path if input.tool_name in {"Edit", "Write", "NotebookEdit"}

# W236: a flag rule fires only on the tool it governs, and only before any quote — a command that
# merely QUOTES the token (a ledger note, a commit message, a grep) is not the forbidden act.

# rule 1: never --no-verify on git (abbreviations are mikemol-hook-no-verify's job)
deny contains "standing 1: never --no-verify" if {
	regex.match(`(^|[\s/;&|])git\s.*\s--no-verify(\s|=|$)`, unquoted)
}

# rule 3: never --nocache_test_results by default
deny contains "standing 3: never --nocache_test_results; the DAG is sound or it is not" if {
	regex.match(`(^|[\s/;&|])bazel\s.*\s--nocache_test_results(\s|=|$)`, unquoted)
}

# rule 7: findings/CENSUS-paperkit-use.md is rosettapkg-db's file
deny contains "standing 7: findings/CENSUS-paperkit-use.md is rosettapkg-db's; file findings to them" if {
	endswith(edited, "findings/CENSUS-paperkit-use.md")
}

# rule 14: warrants are transcribed by mikemol-gen-warrants (formerly .claude/gen_warrants.py) and appended with `>>`, never hand-edited
deny contains "standing 14: warrants.bib is appended from mikemol-gen-warrants output (`>> <dist>/warrants.bib`), not edited" if {
	endswith(edited, "/warrants.bib")
}

# rule 15: a commit message is a file (-F <scratchpad>), never an inline -m/--message
deny contains "standing 15: write the commit message to a scratchpad file and use git commit -F <file>" if {
	regex.match(`(^|[\s/;&|])git\s(.*\s)?commit(\s.*)?\s(-[a-zA-Z]*m[a-zA-Z]*|--message)(\s|=|$)`, unquoted)
}

# rule 12: a git-location variable may point only at a decoy under a temp root. An allowlist of
# decoy roots, not a list of real repos: a new real repo is refused without anyone updating a list.
# Relative values are refused too — they resolve against a cwd the policy cannot see.
git_location_values contains m[2] if {
	some m in regex.find_all_string_submatch_n(
		`(?:^|[\s;&|])(GIT_DIR|GIT_WORK_TREE|GIT_INDEX_FILE|GIT_COMMON_DIR|GIT_OBJECT_DIRECTORY)=["']?([^"'\s;&|]*)`,
		assigned,
		-1,
	)
}

# The command with every quoted span removed EXCEPT one that is an assignment's value
# (GIT_DIR="/x"): a note that quotes an assignment is not one, but a quoted value still is.
# Measured live: rule 12 first read `command` and refused a ledger note quoting `env GIT_DIR=...`.
assigned := regex.replace(command, `([^=]|^)("[^"]*"|'[^']*')`, "${1} ")

decoy_roots := {"/var/tmp/", "/tmp/"}

deny contains "standing 12: point GIT_* location variables only at a decoy repo under /var/tmp/ or /tmp/, never the real one" if {
	some v in git_location_values
	not startswith_any(v, decoy_roots)
}

startswith_any(s, prefixes) if {
	some p in prefixes
	startswith(s, p)
}

# rule 13: every direct pytest run is bounded — `timeout N` kills a hang, and faulthandler_timeout
# dumps the stacks first, so a hang reads as a hang and never as a red. Operator ruling 2026-09-28
# widened this from "arm runs", which the command cannot distinguish, to every pytest run.
pytest_run if regex.match(`(^|[\s/;&|])(pytest|py\.test)(\s|$)`, unquoted)

deny contains "standing 13: run pytest as `timeout 120 <python> -m pytest ... -o faulthandler_timeout=60`" if {
	pytest_run
	not regex.match(`(^|[\s;&|])timeout\s`, unquoted)
}

deny contains "standing 13: run pytest as `timeout 120 <python> -m pytest ... -o faulthandler_timeout=60`" if {
	pytest_run
	not contains(unquoted, "faulthandler_timeout=")
}

# rule 11: the render script is retired; the state tool is mikemol-paths-forward
deny contains "standing 11: paths_forward_render.py is retired; use mikemol-paths-forward" if {
	# in command position (optionally behind an interpreter), not as another program's argument
	regex.match(`(^\s*|[;&|]\s*)(\S*python3?\s+)?\S*paths_forward_render\.py(\s|$)`, command)
}

# rule 16 (W464): no load-bearing code under .claude/ — evidence-producing code is tracked and under
# the bar from its first write. .claude/worktrees/<name>/ is the workflow harness's checkout of the
# repo, so its prefix is stripped (greedily, to the innermost one) before the .claude/ test: a
# worktree's hooks/x.py is ordinary tracked code, while a worktree's own .claude/x.py is not.
claude_code_ext := `\.(py|rego|sh)$`

edited_in_repo := regex.replace(edited, `^.*/\.claude/worktrees/[^/]+/`, "")

# ⚑ A REPO's .claude/, NEVER THE USER's ~/.claude/: that one holds Claude Code's own skills, whose
# scripts are legitimately Python (measured: ~/.claude/skills/synced/.../sheets_helper.py), and is
# no repository's load-bearing code.
home_claude := `^/(home/[^/]+|root)/\.claude/`

deny contains "standing 16: no executable code (.py .rego .sh) under .claude/; put it in a tracked package under the bar" if {
	regex.match(`(^|/)\.claude/`, edited_in_repo)
	not regex.match(home_claude, edited)
	regex.match(claude_code_ext, edited_in_repo)
}

# ---- W238: the (b) rules. Each reads input.facts, which mikemol.hooks.standing_facts gathers
# before opa runs (rego cannot run git or read the queue). A fact that could not be gathered is
# ABSENT, and a rule over an absent fact is undefined: it does not deny on a reading that did
# not happen. Rule 4's Write branch is the exception, below.

# A path a command names, made absolute against the payload's cwd. `git -C <dir>` is not
# followed (residue: such a path resolves against the wrong directory and the rule misses it).
resolve(p) := trim_suffix(p, "/") if startswith(p, "/")

resolve(p) := input.cwd if p in {".", "./"}

resolve(p) := concat("/", [input.cwd, trim_suffix(trim_prefix(p, "./"), "/")]) if {
	not startswith(p, "/")
	not p in {".", "./"}
}

# `a` names `s` itself or a directory holding it.
covers(a, s) if a == s

covers(a, s) if startswith(s, concat("", [a, "/"]))

# The words of each shell segment of the unquoted command.
segment_words contains words if {
	some seg in regex.split(`[;&|]+`, unquoted)
	words := [w | some w in regex.split(`\s+`, trim_space(seg)); w != ""]
}

# rule 9: a STAGED file with a plant is restored by sed, never `git checkout --` (or `git
# restore`, whose default source is the same index): the index holds the planted bytes.
restore_targets contains p if {
	some words in segment_words
	some g, c, d, i
	words[g] == "git"
	c > g
	words[c] == "checkout"
	d > c
	words[d] == "--"
	i > d
	p := words[i]
}

restore_targets contains p if {
	some words in segment_words
	some g, c, i
	words[g] == "git"
	c > g
	words[c] == "restore"
	not index_only(words)
	i > c
	p := words[i]
	not startswith(p, "-")
}

# `git restore --staged` without --worktree rewrites the index, not the planted working file.
index_only(words) if {
	some w in words
	w in {"--staged", "-S"}
	not "--worktree" in words
	not "-W" in words
}

deny contains "standing 9: a STAGED file is restored by sed, never git checkout -- or git restore (the index holds the plant)" if {
	some p in restore_targets
	some s in input.facts.staged
	covers(resolve(p), s)
}

# rule 5 (slice): a hold on a human cannot be lifted from here. Lifting is setting a held row's
# status, kind or blockers away from the human, or dropping it, in the project's own queue.
pf_command if regex.match(`(^|[\s/;&|])mikemol-paths-forward(\s|$)`, unquoted)

pf_state := m[1] if {
	some m in regex.find_all_string_submatch_n(`\s--state[\s=](\S+)`, unquoted, 1)
}

pf_targets contains m[2] if {
	some m in regex.find_all_string_submatch_n(`\s--(update|drop)[\s=](W\d+)(\s|$)`, unquoted, -1)
}

lifts if regex.match(`\s--status[\s=](ready|working|done)(\s|$)`, unquoted)

lifts if regex.match(`\s--blocked-kind[\s=]agent(\s|$)`, unquoted)

# a bare or emptied --blocked-on (`--blocked-on ""` reads as bare once quotes are removed)
lifts if regex.match(`\s--blocked-on(=?\s*$|=?\s+-)`, unquoted)

lifts if regex.match(`\s--drop[\s=]`, unquoted)

deny contains "standing 5: a hold on a human is lifted by the operator, not from here (status, kind, blockers or drop on a held row)" if {
	pf_command
	resolve(pf_state) == input.facts.queue.path
	some w in pf_targets
	w in input.facts.queue.held
	lifts
}

# rule 4: never expand the ratchet baseline (lowering is the operator's call, not refused here).
# Size is its non-blank lines. An Edit is measured from its own old/new strings (residue: an
# Edit with replace_all counts one replacement); a Write against facts.target_lines, the file's
# current size, and a Write whose current size could not be read is REFUSED, because this rule
# guards the baseline itself and an unmeasured rewrite of it is exactly the expansion it forbids.
nonblank(s) := count([l | some l in split(s, "\n"); trim_space(l) != ""])

is_baseline if endswith(edited, "/ratchet-preview.txt")

is_baseline if edited == "ratchet-preview.txt"

rule_4 := "standing 4: never expand the ratchet baseline (ratchet-preview.txt); lowering it is an operator decision"

deny contains rule_4 if {
	is_baseline
	input.tool_name == "Edit"
	nonblank(object.get(input.tool_input, "new_string", "")) > nonblank(object.get(input.tool_input, "old_string", ""))
}

deny contains rule_4 if {
	is_baseline
	input.tool_name == "Write"
	nonblank(object.get(input.tool_input, "content", "")) > object.get(input, ["facts", "target_lines"], -1)
}

# The harness's own deny shape; undefined (no output) when nothing is denied.
decision := {"hookSpecificOutput": {
	"hookEventName": "PreToolUse",
	"permissionDecision": "deny",
	"permissionDecisionReason": concat("; ", sort(deny)),
}} if count(deny) > 0
