# W796: shrink the host katas, do not move them

Notes for the operator, not code. `~/github/.claude/katas/katas.py` (840 lines, 14 subcommands) is
outside this repo; every edit below is a host edit. Read against mtools at commit time of this note;
function names are matched, and where bodies were compared that is said.

## Replace by a call (the mtools tool already does it)

| katas.py | replace with | state |
|---|---|---|
| `prepare_commit`, `commit` | `mikemol-commit REPO --waypoint W --subject S [--body B] [PATH ...]` | bodies compared (W796 evidence): hooks `commit_kata` is a strict superset, and was already graduated by W832. Differences you gain: staged deletions stay pathspecs (W855), no tracked path is NOT COMMITTED instead of `git commit --` over the whole index, and a COMMITTED/REFUSED/NOT COMMITTED line. |
| `wp` title cap (`MAX_TITLE`) | nothing: `mikemol-paths-forward --add` refuses a title over 150 chars that has a `;`, an em dash or ` -- ` (W869) | landed. Note the rule is nemik's, not the katas' length-only cap, so a long single-clause title now passes where `wp` refused it. |
| `gate_red`, `gate_green` | `mikemol-paths-forward --state <repo>/.claude/paths-forward.json --gate-red REASON --next STEP [--blocked-on 'operator: ...'] [--except REPAIRS...]` and `--gate-green EVIDENCE` | landed (W870). The new verbs do NOT set the vector the katas put on the card (`VECTOR` const); add `--update <card> --vector ... --vector-source agent` after, if you want it. They also fix a katas defect: a repair's other `enables` edges were erased. |
| `zram_use` and the 85% refusal in `tick begin` | hooks `tick_gate` (`REFUSE_FRACTION`, `zram_headroom`) | compared by name and constant only. |
| `visit` | `nemik-inbound REPO`, plus the inbound-asks hook for the census | inbox listing (newest first, first line of each letter) has no mtools equivalent; keep that half. |
| `mypy_targets`, `measure`, `count_errors`, `duplicate_files`, `house_mypy` | `mikemol-pycheck --census ROOT` / `--refresh-ledger ROOT`, then `debtplan plan` / `debtplan mint` | NOT the same measurement on purpose: the census counts the edit gate's own verdict (ruff, ruff-format, mypy, syntax) under each project's bar, the katas count mypy alone under HOUSE flags. Switching changes every repo's debt number. Needs your call. |
| `house_ruff` | `mikemol-pycheck --check-file PATH` | katas formats `--isolated` at 88 columns; the gate uses the project's bar. They disagree for any repo with another line length. |
| `closure_frontier`, the closure half of `mypy` | hooks `pycheck_closure` / the advisory hook, from debtplan's graph | bodies NOT compared. |
| `ship` | `typing` + `mikemol-commit` | follows from the two rows above. |

## Stays in katas.py (host orchestration over many repos)

`status`, `pulse`, `archive`, `flush`, `probe`, `precommit_survey`, `start_commit` / `wait` (the
detached commit, which should now spawn `mikemol-commit` as its argv), `tick end` (it acts on the
HOST queue), `bazelize` (host templates), and the policy lists `EXCLUDES`, `EXCL_RE`, `SKIP_TYPING`,
`HOUSE`, `QUEUE_PATHS`.

## Precondition found while writing this

`hooks/.venv/bin/mikemol-commit` DOES NOT EXIST (ls: no such file): the dev venv carries a stale
script set. The LIVE hooks run from the bazel-built venv (`bazel-bin/hooks/.venv`), which does have
`mikemol-commit`, but only behind the `bazel-bin` convenience symlink, which `bazel clean` deletes.
So a katas edit must not name either path. Resolution (2026-10-09, operator ruling on W871 allowed
the edit): `hooks/bin/mikemol-commit` is a tracked launcher at a stable path, the way the hook
launchers beside it are; it resolves the built venv's real path and refuses with the repair named
when the venv or its script is absent. Katas calls `/home/mikemol/github/mtools/hooks/bin/mikemol-commit`.
The module has no `__main__` guard, so `python -m mikemol.hooks.commit_kata` does nothing.

## Not known

- `measure`'s second pass for mypy's "Duplicate module named" clash (gcalc.py beside gcalc/): the
  census judges files singly, so it may not need it; unmeasured.
- Where the typing ledger lives: katas writes `ledgers/<repo>.json` on the host; the census
  `--refresh-ledger` writes inside the repo. Choosing is a layout decision.
- No test exists for katas.py (none seen in the outline), so a shrink has no regression net except
  the mtools tools' own tests; run `katas.py status` and `pulse` before and after.

## Order that keeps the loop alive

1. `commit` first (smallest, already proven): point `start_commit` and `commit` at `mikemol-commit`.
2. `wp` and the gate pair next (they only call the queue writer).
3. typing/mypy last, after you choose the measurement and the ledger location.
