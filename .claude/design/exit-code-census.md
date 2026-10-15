# Exit-code census (W1290, input to W1266)

Notes, not code. Source: every `EXIT_<NAME> = <int>` assignment under `fence/src`, `pathsforward/src`
and `hooks/src` at mtools 9cbc3d4 plus the working tree (grep, 2026-10-15). Not read: luthen's
`apply_set.py` (its `EXIT_DEFERRED = 3` is github-8f's claim, unverified here), summit, substrate,
gabion. A negative about those is "not in what I read".

## By value: where one number carries more than one meaning

| value | meanings found (module) |
|---|---|
| 0 | OK / ADMITTED / FORMATTED / INSTALLED (consistent) |
| 1 | FAILED (probe, revendor, musthave, repin, wheel), REFUSED (pycheck_cli, pycheck_install, pycheck_clear), FINDINGS (websubset), NOT_COMMITTED (commit_kata), LOCK (membudget) |
| 2 | USAGE (guard, membudget, pycheck_cli, probe, snapshot, vlogcli and others; consistent) **and** REFUSED (pathsforward cli, flag_contract, hook_argv, new_dist_cli), FEEDBACK (build_failure), UNTRANSCRIBABLE (gen_warrants) |
| 3 | REFUSED (fence admit, bazel_admit, work_claims_hook), LOCKED (pathsforward), NOT_CHECKED (pycheck_cli, pycheck_install), NOT_RUN (pycheck_format, pycheck_clear), NOT_TAKEN (snapshot), NO_CAP (membudget), NO_DESTINATION (vlogcli) |
| 4 | LEDGER (fence admit), DIVERGED (pathsforward), RACED (commit_kata, stackrun), REFUSED (vlogcli) |
| 5 | BUSY (vlogcli) |
| 6 | HELD (vlogcli) |
| 125-127 | HARNESS, NOT_EXECUTABLE, NOT_FOUND (fence core, shell convention); NOT_STARTED 127 (vlogforms) |

## What it shows

- **REFUSED has three values**: 1 (pycheck family), 2 (pathsforward, flag contract, new dist), 3
  (fence admit, bazel_admit, work claims) and 4 (vlogcli). A caller that branches on "refused"
  must know the tool.
- **2 is both usage and refusal** inside one dist (pathsforward: `EXIT_REFUSED = 2` where hooks
  uses 2 for usage and 1 for refusal).
- **3 is the busiest value** with seven names. The fence-versus-luthen collision W1266 names
  (REFUSED vs DEFERRED) is one instance of a wider pattern: 3 is "the thing I was asked for was not
  done and the reason is not an error" under seven names.
- Consistent already: 0, usage = 2 (mostly), 125-127.

## Not decided here

The codomain (DONE NOOP DEFER REFUSE WITHHELD RACE) and which value each takes is W1266's design
step; this census only fixes what exists. A fleet table must also decide whether usage keeps 2
(the shell and argparse convention) and so forces REFUSED off 2, which moves pathsforward's
`EXIT_REFUSED`, a value its callers (katas, hooks, the stop hook) already read.
