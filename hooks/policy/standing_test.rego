# Each rule: a witness that must deny, and a near-miss control that must not.
package mtools.hook_test

import rego.v1

import data.mtools.hook

bash(cmd) := {"tool_name": "Bash", "tool_input": {"command": cmd}}

edit(path) := {"tool_name": "Edit", "tool_input": {"file_path": path}}

denies(inp, n) if {
	some msg in hook.deny with input as inp
	startswith(msg, sprintf("standing %d:", [n]))
}

test_1_witness if denies(bash("git commit --no-verify -F /tmp/m"), 1)

test_1_control if not denies(bash("git commit -F /tmp/no-verify-notes"), 1)

test_3_witness if denies(bash("bazel test //... --nocache_test_results"), 3)

test_3_control if not denies(bash("bazel test //..."), 3)

test_7_witness if denies(edit("/home/mikemol/github/mtools/findings/CENSUS-paperkit-use.md"), 7)

test_7_control if not denies(edit("/home/mikemol/github/mtools/findings/CENSUS-other.md"), 7)

test_14_witness if denies(edit("/home/mikemol/github/mtools/hooks/warrants.bib"), 14)

test_14_write_witness if denies({"tool_name": "Write", "tool_input": {"file_path": "/home/mikemol/github/mtools/mdstruct/warrants.bib"}}, 14)

test_14_control if not denies(edit("/home/mikemol/github/mtools/hooks/rubric.tsv"), 14)

test_14_append_control if not denies(bash("mikemol-gen-warrants hooks cmdparse=X >> hooks/warrants.bib"), 14)

# the module form, which a venv without the console script uses (W501)
test_14_module_append_control if not denies(bash("hooks/.venv/bin/python3 -m mikemol.hooks.gen_warrants hooks cmdparse=X >> hooks/warrants.bib"), 14)

test_16_py_witness if denies(edit("/home/mikemol/github/mtools/.claude/design/probe.py"), 16)

test_16_write_rego_witness if denies({"tool_name": "Write", "tool_input": {"file_path": "/home/mikemol/github/mtools/.claude/x.rego"}}, 16)

test_16_relative_sh_witness if denies(edit(".claude/swarm3/run.sh"), 16)

# a worktree's own .claude/ is still .claude/
test_16_worktree_claude_witness if denies(edit("/r/.claude/worktrees/wf_1/.claude/tool.py"), 16)

test_16_worktree_control if not denies(edit("/home/mikemol/github/mtools/.claude/worktrees/wf_1/hooks/src/x.py"), 16)

test_16_notes_control if not denies(edit("/home/mikemol/github/mtools/.claude/design/notes.md"), 16)

test_16_outside_control if not denies(edit("/home/mikemol/github/mtools/hooks/src/claude.py"), 16)

test_16_lookalike_control if not denies(edit("/home/mikemol/github/mtools/not.claude/x.py"), 16)

# the user's ~/.claude/ is Claude Code's own (skills ship Python), not a repo's load-bearing code
test_16_home_claude_control if not denies(edit("/home/mikemol/.claude/skills/x/scripts/helper.py"), 16)

test_16_root_claude_control if not denies(edit("/root/.claude/skills/x/run.sh"), 16)

test_15_witness if denies(bash("git commit -m \"subject\""), 15)

test_15_bundled_witness if denies(bash("git -C /r commit -am \"subject\""), 15)

test_15_long_witness if denies(bash("git commit --message=subject"), 15)

test_15_control if not denies(bash("git -C /r commit -F /tmp/msg.txt"), 15)

test_15_amend_control if not denies(bash("git commit --amend -F /tmp/msg.txt"), 15)

test_15_quoted_control if not denies(note("git commit -m is refused"), 15)

test_15_other_subcommand_control if not denies(bash("git tag -m x v1"), 15)

test_12_witness if denies(bash("GIT_DIR=/home/mikemol/github/mtools/.git git log"), 12)

test_12_env_witness if denies(bash("env GIT_WORK_TREE=/home/mikemol/github/mtools git status"), 12)

test_12_quoted_value_witness if denies(bash("GIT_DIR=\"/home/mikemol/github/x/.git\" git log"), 12)

test_12_relative_witness if denies(bash("GIT_DIR=.git git log"), 12)

test_12_decoy_control if not denies(bash("GIT_DIR=/var/tmp/claude-1000/s/decoy/.git git log"), 12)

test_12_quoted_decoy_control if not denies(bash("GIT_INDEX_FILE='/tmp/decoy/index' git add x"), 12)

test_12_plain_git_control if not denies(bash("git -C /home/mikemol/github/mtools status"), 12)

test_12_quoted_note_control if not denies(note("live env GIT_DIR=/home/mikemol/github/mtools/.git refused"), 12)

test_12_substring_control if not denies(bash("MYGIT_DIR=/home/x true"), 12)

test_13_bare_witness if denies(bash("env -C hooks .venv/bin/python -m pytest -q tests"), 13)

test_13_no_faulthandler_witness if denies(bash("timeout 120 .venv/bin/python -m pytest -q"), 13)

test_13_no_timeout_witness if denies(bash(".venv/bin/pytest -q -o faulthandler_timeout=60"), 13)

test_13_control if not denies(bash("timeout 120 .venv/bin/python -m pytest -q -o faulthandler_timeout=60"), 13)

test_13_bazel_control if not denies(bash("bazel test //hooks:pytest"), 13)

test_13_quoted_control if not denies(note("ran pytest -q, all green"), 13)

test_13_path_word_control if not denies(bash("cat hooks/tests/pytest.ini"), 13)

test_11_witness if denies(bash("python3 .claude/paths_forward_render.py"), 11)

test_11_control if not denies(bash("pathsforward/.venv/bin/mikemol-paths-forward --render"), 11)

# W236: a command that only QUOTES a token (a ledger note, a grep) is not the act the rule forbids.
note(text) := bash(sprintf("mikemol-paths-forward --ledger W1 done sweep \"%s\"", [text]))

test_1_quoted_control if not denies(note("never --no-verify here"), 1)

test_3_quoted_control if not denies(note("never --nocache_test_results by default"), 3)

test_11_quoted_control if not denies(note("paths_forward_render.py is retired"), 11)

test_11_grep_control if not denies(bash("grep -rn paths_forward_render.py .claude"), 11)

test_3_quote_naming_bazel_control if not denies(note("scoped to git/bazel then --nocache_test_results here"), 3)

test_1_quote_naming_git_control if not denies(note("git then --no-verify here"), 1)

test_3_flag_after_target if denies(bash("bazel test //hooks/... --nocache_test_results"), 3)

test_11_direct_exec if denies(bash(".claude/paths_forward_render.py --render"), 11)

# W238: rules that read input.facts, gathered by mikemol.hooks.standing_facts before opa runs.
in_repo(cmd, staged) := {
	"tool_name": "Bash",
	"tool_input": {"command": cmd},
	"cwd": "/r/sub",
	"facts": {"staged": staged},
}

test_9_witness if denies(in_repo("git checkout -- plant.py", ["/r/sub/plant.py"]), 9)

test_9_absolute_witness if denies(in_repo("git checkout -- /r/sub/plant.py", ["/r/sub/plant.py"]), 9)

test_9_dot_slash_witness if denies(in_repo("git checkout HEAD -- ./plant.py", ["/r/sub/plant.py"]), 9)

test_9_directory_witness if denies(in_repo("git checkout -- .", ["/r/sub/deep/plant.py"]), 9)

test_9_restore_witness if denies(in_repo("git restore plant.py", ["/r/sub/plant.py"]), 9)

test_9_unstaged_control if not denies(in_repo("git checkout -- other.py", ["/r/sub/plant.py"]), 9)

test_9_prefix_control if not denies(in_repo("git checkout -- plant", ["/r/sub/plant.py"]), 9)

test_9_branch_control if not denies(in_repo("git checkout main", ["/r/sub/main"]), 9)

test_9_restore_staged_control if not denies(in_repo("git restore --staged plant.py", ["/r/sub/plant.py"]), 9)

test_9_no_fact_control if not denies(bash("git checkout -- plant.py"), 9)

test_9_quoted_control if not denies(in_repo("mikemol-paths-forward --ledger W1 x y \"git checkout -- plant.py\"", ["/r/sub/plant.py"]), 9)

queue_path := "/p/.claude/paths-forward.json"

pf(args) := {
	"tool_name": "Bash",
	"tool_input": {"command": sprintf("mikemol-paths-forward --state %s %s", [queue_path, args])},
	"cwd": "/p",
	"facts": {"queue": {"path": queue_path, "held": ["W7"]}},
}

test_5_status_witness if denies(pf("--update W7 --status ready"), 5)

test_5_status_equals_witness if denies(pf("--update W7 --status=working"), 5)

test_5_kind_witness if denies(pf("--update W7 --blocked-kind agent"), 5)

test_5_empty_blocked_on_witness if denies(pf("--update W7 --blocked-on \"\""), 5)

test_5_bare_blocked_on_witness if denies(pf("--update W7 --blocked-on --next x"), 5)

test_5_drop_witness if denies(pf("--drop W7 superseded"), 5)

test_5_relative_state_witness if denies(
	{
		"tool_name": "Bash",
		"tool_input": {"command": "mikemol-paths-forward --state .claude/paths-forward.json --update W7 --status ready"},
		"cwd": "/p",
		"facts": {"queue": {"path": queue_path, "held": ["W7"]}},
	},
	5,
)

test_5_unheld_control if not denies(pf("--update W8 --status ready"), 5)

test_5_evidence_control if not denies(pf("--update W7 --evidence-append \"asked again\""), 5)

test_5_keeps_hold_control if not denies(pf("--update W7 --blocked-on operator --next x"), 5)

test_5_symbol_prefix_control if not denies(pf("--update W70 --status ready"), 5)

test_5_other_queue_control if not denies(
	{
		"tool_name": "Bash",
		"tool_input": {"command": "mikemol-paths-forward --state /q/other.json --update W7 --status ready"},
		"cwd": "/p",
		"facts": {"queue": {"path": queue_path, "held": ["W7"]}},
	},
	5,
)

test_5_no_fact_control if not denies(bash(sprintf("mikemol-paths-forward --state %s --update W7 --status ready", [queue_path])), 5)

baseline_edit(old, new) := {"tool_name": "Edit", "tool_input": {
	"file_path": "/r/hooks/ratchet-preview.txt",
	"old_string": old,
	"new_string": new,
}}

test_4_grow_witness if denies(baseline_edit("a:1\n", "a:1\nb:2\n"), 4)

test_4_from_empty_witness if denies(baseline_edit("", "b:2\n"), 4)

test_4_shrink_control if not denies(baseline_edit("a:1\nb:2\n", "a:1\n"), 4)

test_4_same_count_control if not denies(baseline_edit("a:1\n", "a:2\n"), 4)

test_4_blank_line_control if not denies(baseline_edit("a:1\n", "a:1\n\n"), 4)

test_4_other_file_control if not denies(
	{"tool_name": "Edit", "tool_input": {
		"file_path": "/r/hooks/rubric.tsv",
		"old_string": "",
		"new_string": "b:2\n",
	}},
	4,
)

baseline_write(content, facts) := {
	"tool_name": "Write",
	"tool_input": {"file_path": "/r/hooks/ratchet-preview.txt", "content": content},
	"facts": facts,
}

test_4_write_witness if denies(baseline_write("a:1\nb:2\n", {"target_lines": 1}), 4)

# a Write over a baseline whose current size could not be read is refused (fail closed)
test_4_write_unread_witness if denies(baseline_write("a:1\n", {}), 4)

test_4_write_lower_control if not denies(baseline_write("a:1\n", {"target_lines": 2}), 4)

test_4_write_same_control if not denies(baseline_write("a:1\nb:2\n", {"target_lines": 2}), 4)

test_read_is_never_denied if {
	count(hook.deny) == 0 with input as {"tool_name": "Read", "tool_input": {"file_path": "findings/CENSUS-paperkit-use.md"}}
}
