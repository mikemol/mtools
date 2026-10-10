# W939: the pre-commit gate under an isolated commit finds its tools (2026-10-10)

Measured. The first isolated commit (W937, soak 1) was refused before any check ran:
`pre-commit: atomicwrite/.venv/bin/ruff not found`. The gate ran with cwd and `git rev-parse
--show-toplevel` = the snapshot (`/var/tmp/mikemol/gate/mtools/tree`), which holds the tracked tree
and nothing else. `<dist>/.venv` and `bazel-bin/` are untracked build outputs of the REAL checkout.

What the gate reads from "the checkout" (`.githooks/pre-commit`, 1222 lines):

- the tree it gates: from the INDEX (`git checkout-index --all --prefix=$staged/`), so under an
  isolated commit it is already the private index's tree. Correct, and independent of cwd.
- tools: `$dist/.venv/bin/{ruff,mypy,python3}` for every distribution (presence loop, line ~324),
  `ratchet/.venv/bin/mikemol-ratchet` (~346), `mdstruct/.venv/bin/python3` (~1007-1119),
  `hooks/.venv/bin/python3` (~983), `bazel-bin/ratchet/...`, `bazel-bin/hooks/.venv/...` (~146-152).
- bazel itself: `cd $root && bazel build //ratchet:ratchet_cli //<dist>:.venv ...` (~514). In the
  snapshot this is the snapshot's own workspace: its output base is hashed from the FIXED path, so
  after one cold run it stays warm (the operator's 2026-10-06 ruling). It builds `bazel-bin/<dist>/.venv`
  there.

So the gate has two ways to find a venv, and the isolated case needs the second:

1. `<dist>/.venv/bin/X` (a path in the checkout; present in the real tree only);
2. `bazel-bin/<dist>/.venv/bin/X` (present in ANY workspace that ran `bazel build //<dist>:.venv`,
   which the gate does at ~514, AFTER the presence loop that refused).

## MEASURED 2026-10-10 (W940): THE FIRST DRAFT OF THIS DECISION WAS WRONG

`bazel build //atomicwrite:.venv` in the snapshot succeeded (26 s, warm disk cache), and
`bazel-bin/atomicwrite/.venv/bin/` holds `python3` ONLY: no `ruff`, no `mypy`, no `pytest`. The
real tree's `atomicwrite/.venv` is a different thing: a uv-created host venv (dated Oct 4, 23 MB
`ruff` binary, console scripts, `python -> /usr/lib/python-exec/...`). So the bazel artifact is not a
substitute for the host venv, and a `bazel-bin` fallback (2) supplies nothing the gate runs.

## Decision (revised)

The tools are HOST state and come from the real checkout; the TREE comes from the index. One shell
function, `venv_bin DIST TOOL`, prints `${MIKEMOL_REAL_ROOT:-$root}/$DIST/.venv/bin/$TOOL`, and the
presence loops, the singleton check and every call site go through it. `isolated.commit_isolated`
exports `MIKEMOL_REAL_ROOT` (the real worktree) to the commit; unset, `venv_bin` is today's path,
so a normal commit is unchanged. The `bazel-bin` lookups (~146-152, ~532) stay in the snapshot's own
workspace, which the prebuild populates. Nothing is copied or linked into the snapshot (no links,
operator 2026-10-02), and the staged copy still comes from `git checkout-index` over the index.

Mechanized, not hand-fixed: `test_bar_fires` already derives populations from this file. A new arm
refuses any `.venv/bin/` outside `venv_bin`, so the next call site added cannot reintroduce the
snapshot-blind lookup. (`rules_py/venv.bzl` counts the call sites by hand: "12", then "13", and
admits its own count drifted.)

## Slices

| card | what |
| --- | --- |
| W940 | `venv_bin` in `.githooks/pre-commit` and every `.venv/bin/` call site through it; the presence loops after the prebuild; a `test_bar_fires` arm that no raw `.venv/bin/` survives outside it. Live hook: deps first, live file last (memory live-hook-dependencies-first). |
| W941 | an isolated-mode end-to-end on a decoy repo whose pre-commit needs a tool only the real root has (the gate is not run; the stand-in hook is). |
| W904 | then the soak resumes. |

## Open

- Does `bazel build //<dist>:.venv` in the snapshot leave `bazel-bin/<dist>/.venv/bin/ruff` runnable
  from a different workspace path (the absolute interpreter link in `venv.bzl` says yes)? W940 measures
  it first, on one distribution, before touching the hook.
- The editable installs name `$root/<dist>/src`; in the snapshot that is the snapshot's own src, which
  is what an isolated gate should import. The hook already sets `PYTHONPATH`/`MYPYPATH` to the staged
  tree, so the two agree.
