# W231 — standing rules → hook-enforced OPA

Source: luthen-observability-81 reply, 2026-09-28 (their classification over mtools' first guess).

## Harness shape (copy, not reuse — luthen has no PreToolUse harness)

- hook script builds `{tool_name, tool_input, cwd, facts:{...}}`; facts gathered by file/git reads BEFORE opa
- `opa eval -f json -i <input> -d policy data.mtools.hook`; exit 2 with deny messages; every deny names its rule number
- `*_test.rego` run by the gate
- a NEGATIVE WITNESS per rule: a real input replayed with the exception removed must deny

## Classification

| # | rule | class | predicate / facts |
|---|---|---|---|
| 1 | never --no-verify | a | |
| 2 | never edit .bazelrc / settings.json | a (Edit/Write); Bash weaker | deny unconditionally on path; the motive ("to escape a refusal") is c |
| 3 | never --nocache_test_results | a | |
| 4 | never expand ratchet baseline | b | count before vs after, from old_string/new_string |
| 5 | peer cannot lift a hold | c + b slice | b: deny `--update W --status ready`/empty `--blocked-on` when row has blocked_kind=human |
| 6 | paperkit freeze / embargo | a (path) + b (freeze) | facts = freeze record, so it lifts with the record |
| 7 | CENSUS-paperkit-use.md not ours | a | |
| 8 | blocked-human asked same turn | c at PreToolUse; b as Stop hook | new blocked-human rows vs AskUserQuestion in transcript |
| 9 | plant restored by sed, not checkout | b | `git diff --cached --name-only`; deny `git checkout -- P` for staged P |
| 10 | don't cite parse_requirements docstring | c | |
| 11 | state tool is mikemol-paths-forward | a | |
| 12 | GIT_* never at the real repo | a | data doc of real repo paths; resolve cwd-relative forms |
| 13 | arms under timeout 120 + faulthandler | a (wrapper) + c (behaviour) | |
| 14 | warrants via gen_warrants.py | a | deny Edit/Write to warrants.bib |
| 15 | commit -F scratchpad, run_in_background | a | deny `git commit -m`; deny commit/preflight with run_in_background false |
| 16 | gate TIMEOUT retry | c | |
| 17 | probes via scratchpad | a | needs a recognizable probe name/dir |
| 18 | swarm read-only / one commit per tick | b + c | identity: VERIFY hook input carries agent_type/agent_id (unverified); commits since lock taken_at |
| 19 | lost symbol recovered from transcripts | c | |

## Batch 1 — wired 2026-09-28, removed from standing (verbatim, residue)

Hook: `hooks/bin/mikemol-hook-standing` → `hooks/policy/standing.rego`; settings.json PreToolUse
`Bash|Edit|Write|NotebookEdit`. Live replay denied all four.

- rule 1: `never --no-verify`
- rule 3: `never --nocache_test_results by default — the DAG is sound or it is not`
- rule 7: `findings/CENSUS-paperkit-use.md is rosettapkg-db's file (landed at 4683280); do not edit it — file findings to them`
- rule 11 (clause only): `.claude/paths_forward_render.py is retired` — the positive half ("the state tool is mikemol-paths-forward … re-arm from its --payload") stays in standing

Known false positive: rules 3 and 11 match the token anywhere in a Bash command, so a command that
merely QUOTES it (a ledger note, a grep) is refused. Measured on the batch-1 ledger write.

## Constraint

Wiring any hook into `.claude/settings.json` is an operator decision; a tick drafts policy + tests + witnesses only.
