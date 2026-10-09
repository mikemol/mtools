<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# mikemol-katas

The host orchestration katas, graduated into a tracked distribution (mtools:W796). The host's
`~/github/.claude/katas/katas.py` sits under `.claude/`, where standing rule 16 refuses executable
code, so it cannot be edited in place; what it does that no mtools tool already does lives here, and
it calls those tools (`mikemol-commit`, `mikemol-pycheck --census`, `mikemol-paths-forward
--gate-red`) for the rest.

`mikemol-katas [--policy FILE] SUBCOMMAND ...` has the host katas' subcommand names:
`status | pulse | flush | probe | archive | precommit | bazelize | tick | commit`. The ones an mtools
tool now does (`wp gate typing mypy ship visit`) print the exact command to run instead and exit 2.

Every host value (the root, the skip list, the tool paths, the lock holder, the bazel version, the
standing nemik warnings) is read from a TOML policy file, `~/.config/mikemol/katas.toml` or
`$XDG_CONFIG_HOME/mikemol/katas.toml`, never from a constant; `mikemol.katas.policy` names every
required key when one is absent.

| module | does |
|---|---|
| `workstreams` | `repos(root)` names the directories that carry a queue |
| `commits` | `commit_argv` builds the `mikemol-commit` argv; `commit_state(log)` reads a detached commit's log |
| `waiter`, `detach` | run a command to its end leaving `rc=N` in its log; start one detached |
| `fleet` | git state per workstream: `status`, `flush`, `probe` |
| `inbox` | `archive` handled letters, never overwriting an archived name |
| `survey` | each repo's pre-commit hook: where it is, whether it invokes bazel |
| `scaffold` | bazel files from templates, and the hook swap once `//:precommit` passed |
| `pulse` | the fleet view with nemik's warnings and the top of its ranking |
| `hosttick` | the host queue's tick lock and the order a tick closes in |
| `policy`, `cli` | the policy file, and the command line over all of the above |
