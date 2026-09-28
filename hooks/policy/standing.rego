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

# rule 14: warrants are transcribed by gen_warrants.py and appended with `>>`, never hand-edited
deny contains "standing 14: warrants.bib is appended from gen_warrants.py output (`>> <dist>/warrants.bib`), not edited" if {
	endswith(edited, "/warrants.bib")
}

# rule 11: the render script is retired; the state tool is mikemol-paths-forward
deny contains "standing 11: paths_forward_render.py is retired; use mikemol-paths-forward" if {
	# in command position (optionally behind an interpreter), not as another program's argument
	regex.match(`(^\s*|[;&|]\s*)(\S*python3?\s+)?\S*paths_forward_render\.py(\s|$)`, command)
}

# The harness's own deny shape; undefined (no output) when nothing is denied.
decision := {"hookSpecificOutput": {
	"hookEventName": "PreToolUse",
	"permissionDecision": "deny",
	"permissionDecisionReason": concat("; ", sort(deny)),
}} if count(deny) > 0
