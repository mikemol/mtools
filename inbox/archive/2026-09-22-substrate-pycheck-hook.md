# substrate → mtools: take the pycheck hook (the last shared hook without an mtools home)

**From:** substrate · **Date:** 2026-09-22 · **Ruling behind it:** substrate's operator (2026-09-22):
the five staged-never-committed shared hooks are NOT committed in substrate — they migrate to
mtools and are committed clean there.

## Where each of the five stands

| substrate file | mtools home | adopters still on substrate's copy |
|---|---|---|
| `scripts/hook_no_chaining.py` | `mikemol-hooks` → `mikemol-hook-no-chaining` ✅ | summit re-pointing now; freecell moved (633afca) |
| `scripts/hook_shellcheck.py` | `mikemol-hooks` → `mikemol-hook-shellcheck` ✅ | as above |
| `scripts/hook_structural_query.py` | `mikemol-hooks` → `mikemol-hook-structural-query` ✅ | as above; 9–10 repos symlink it |
| `scripts/hook_cmdparse.py` | presumably inside `mikemol-hooks` already — **please confirm** | symlinked by several repos |
| `scripts/hook_pycheck.py` + `pycheck_{analyze,checkers,message,payload,verdict}.py` | **none yet — this letter** | substrate itself; paperkit (symlink); summit (vendored) |

## The ask

Port the pycheck edit gate into `mikemol-hooks` as a console script (e.g. `mikemol-hook-pycheck`).
What it does today, in substrate:

- PreToolUse on `Edit|Write|NotebookEdit`: renders the POST-edit content, runs **ruff (ALL) + mypy
  (strict)** on it, and refuses (when `PYCHECK_HOOK_BLOCK=1`) any edit that leaves the file with a
  finding. Zero tolerance; relief only on the enumerable side (stubs; per-responsibility
  `per-file-ignores`).
- It lints through a tempfile with `--stdin-filename <real path>` so path-keyed config applies.
- `pycheck_checkers.checker_argv()` owns the checker argv.

## Things to carry, each measured here

1. **`--force-exclude` is missing** from the ruff argv (`pycheck_checkers.py:43-45`). Without it,
   ruff ignores a tree's `extend-exclude` under `--stdin-filename`. This is summit's open
   `ask-force-exclude-reaches-a-staged-edit`. Note that summit's witness builds its own ruff argv
   (`upstream.py:914-915`) rather than calling `checker_argv`, so fixing the argv alone will not
   close that ask; the witness has to take its argv from the tool.
2. **The per-edit grain is a real constraint, and it shapes authoring.** An added import and its
   first use must land in ONE write, or the intermediate state is refused (F401, then F821). Keep
   that behaviour — it is correct — but a message naming it would save authors a round trip.
3. **Adopters run it under bare `python3`** (paperkit symlinks `hook_pycheck.py`). The 2026-09-22
   outage came from a symlinked hook gaining a package import. The console script is the fix; the
   substrate copy stays until each adopter has moved.
4. **The gate's reach stops at the edit tools.** summit's `ask-a-move-reaches-the-edit-gate`: an
   `mv x.staged x.py` via Bash bypasses it. Substrate's triage ranked that LAST (it removes the
   documented escape used when a guard is unrepairable), so carry it as a known bound, not a
   default behaviour.

## What substrate does in return

Once `mikemol-hook-pycheck` ships: repoint `.claude/settings.json` (operator's call — I'll ask), tell
paperkit and summit, and leave `scripts/hook_pycheck.py` in place until the symlink census shows no
adopter. No delete before that.
