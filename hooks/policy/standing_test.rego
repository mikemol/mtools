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

test_14_append_control if not denies(bash("python3 .claude/gen_warrants.py hooks cmdparse=X >> hooks/warrants.bib"), 14)

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

test_read_is_never_denied if {
	count(hook.deny) == 0 with input as {"tool_name": "Read", "tool_input": {"file_path": "findings/CENSUS-paperkit-use.md"}}
}
