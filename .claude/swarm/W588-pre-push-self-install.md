# W588: mtools pre-push self-install against the post-commit auto-push

Measured 2026-10-04 in a scratch clone (`--no-hardlinks`) of mtools at 72436f1 pushing to a local bare remote; the
real repo, its `.git` and its `.githooks` were never touched. The stub was
`.githooks/pre-push` = `exec <hooks venv>/bin/mikemol-githook-pre-push "$@"` (the real console script, present in
`hooks/.venv/bin`), with a recorder installed as `.githooks/pre-push.local` that logs argv, stdin, `HEAD`, the guard
variable and whether each pushed sha carries the marker, and exits 7 when a flag file exists.

## Measurements

| Q | Procedure | Measured result |
| --- | --- | --- |
| (a) invoked? recursion? | commit with the real `.githooks/post-commit` | Yes: the auto-push ran pre-push once, then
pre-push.local once. No re-entry: pre-push does not commit, so post-commit never re-fires from it. |
| (b) pre-push fails | flag file present, commit | Push abandoned before any object transfer; remote stayed at the old
sha; the commit survived locally; `git commit` exit 0. post-commit printed "PUSH REFUSED, the remote has moved", which
is a MISDIAGNOSIS: the real cause (pre-push exit 7) appears only in two stderr lines above it. Next commit pushed
both. |
| (c) stdin shape | recorder log | argv `origin <url>`; one line `HEAD <local sha> refs/heads/main <remote sha>`
(local ref is the literal `HEAD`, from the `HEAD:main` refspec). When already up to date the hook still runs, stdin
empty. |
| (d) marker amend | post-commit with the marker hook run before the push (see limits) | The amend re-fires mtools'
post-commit, which has no `_POST_COMMIT_AMENDING` guard. The nested push (guard set) pushes the AMENDED sha; pre-push
saw the marker in it. The outer push then found "Everything up-to-date", so pre-push ran a SECOND time with empty
stdin. The original sha was never pushed. The nested output is captured by the amend, so the operator sees one push
line, naming the amended sha. |
| (e) core.hooksPath | `git config core.hooksPath .githooks` | Relative value, per-clone `.git/config`, set by setup.sh
line 20, not tracked. Hooks run from the toplevel, so `.githooks/pre-push` resolved. A fresh clone without setup.sh
runs no pre-push at all, same as every other mtools hook. |

## Limits of the measurement

- The scratch pre-commit was a stand-in that records the tree in the witness file; the real gate was not run, and the
  commit-msg hook was removed.
- mtools' real post-commit does NOT call the marker hook today. (d) used a scratch edit inserting it before the push.
  The `mikemol-githook-post-commit` console script is ABSENT from `hooks/.venv/bin` (stale sync), so it ran as
  `python -m mikemol.hooks.githook_post_commit` with PYTHONPATH=hooks/src. The advisory body was only the header
  (no post-commit.local exists).
- Empty commits, local-path remote, no concurrent writer, no second session pushing; a real diverged remote and
  GitHub's server-side hooks were not measured. A failing pre-push combined with the marker amend was not measured.
- The stub used an absolute venv path; a repo-relative path relies on git running hooks from the toplevel
  (documented, consistent with (e), not separately measured).
- Timing is wall only: pre-push added tens of milliseconds (log timestamps); not benchmarked.

## Recommendation

Install, with two conditions. It blocks a push while a rebase, merge or cherry-pick is in flight and gives the repo
the `pre-push.local` extension point at no change to commit behaviour; it cannot lose a commit.

1. Fix the misdiagnosis in `.githooks/post-commit`: the refusal text must not say "the remote has moved" when pre-push
   refused. Separate waypoint.
2. If the marker hook is later wired into post-commit, add the `_POST_COMMIT_AMENDING` guard to the push, or accept
   the double push (two pre-push runs per commit).

Stub text for `.githooks/pre-push` (executable bit set, mode 100755):

    #!/usr/bin/env bash
    exec hooks/.venv/bin/mikemol-githook-pre-push "$@"

Order of operations, live:

1. Confirm `hooks/.venv/bin/mikemol-githook-pre-push` runs (`--help` is not defined; run it with empty stdin in a
   scratch clone) and, if wiring the marker hook, re-sync the venv so `mikemol-githook-post-commit` exists.
2. Land any dependency first: the `.githooks/pre-push.local` policy, if one is wanted, executable.
3. Write `.githooks/pre-push` LAST, with the executable bit, and commit it. It is live on the next push.
4. Recovery if pushes lock out: `git checkout HEAD -- .githooks/pre-push` (or the previous file), or `git push` once
   after removing the file; commits are never affected.
