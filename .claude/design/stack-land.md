# Stack-land: several commits, one gate (W1155, W1156; neighbour W1100)

Asked by luthen via github-8f: 13 lands in 298 min, median 11.4 min each, one idea per gate, 52
percent of the wall in the serial gate; 6 of 13 could have shared a gate (about 50 min).

## Why it is possible

`git commit` runs the repo's hooks; plumbing does not. So the commits can be BUILT without hooks and
the gate run ONCE on the tip, then HEAD moved only if it passed.

1. For each entry k (waypoint, subject, body, paths), in order: tree_k = tree_(k-1) plus entry k's
   paths, built in a private index exactly as `isolated.commit_isolated` builds one
   (`read-tree`, `add -A`/`add -f`, `write-tree`). commit_k = `git commit-tree tree_k -p commit_(k-1)`
   with the message and the waypoint trailer. Each commit holds only its own paths on top of the one
   before, so blame stays per card.
2. Materialize tree_n (the tip) at the fixed snapshot path and run the gate once there:
   `git hook run pre-commit` with the same GIT_DIR / GIT_WORK_TREE / GIT_INDEX_FILE /
   MIKEMOL_REAL_ROOT environment `commit_isolated` uses. The commit-msg hook runs per message
   (cheap), also through `git hook run`.
3. If the gate passes: `git update-ref HEAD commit_n <the HEAD read at the start>`. A moved HEAD
   fails the update (the old value no longer matches): that is RACED, exit 4, nothing landed. Then
   the real index is refreshed for the union of paths (`refresh_index`), and ONE push follows,
   verified by `published()`.
4. A verdict line per commit: `COMMITTED mtools <sha7> <subject> [PUSHED]` for each, in order.

## Refusal (W1156): all or nothing

If the gate refuses, no ref moves. The failing check names its paths; each is mapped to the entry
whose paths contain it and the verdict says `REFUSED stack: entry <k> (<waypoint>) holds <path>`.
Landing "the prefix before the culprit" would need a SECOND gate run on that prefix's tip (the tip
that was gated includes the culprit), so it is not done silently: the verdict names the culprit and
the caller re-submits the shorter stack. What landed is always stated: nothing.

## Pieces (each its own card, tests against real git as test_commit_isolated_*)

- W1160 the stack plan and its plumbing: parse repeated entries, build tree_k and commit_k, return the
  chain; pure over a runner, tested on a throwaway repo (blame per entry, trailers, order).
- W1161 gate once on the tip with `git hook run`, update-ref against the starting HEAD (RACED), real
  index refresh, one push, one verdict per commit.
- W1156 failing check path to entry attribution and the all-or-nothing verdict.
- W1162 the `mikemol-commit` argument form: repeated `--stack WAYPOINT SUBJECT PATH...` (body from
  `--body-file`), routed in `commit_kata.parse`; a single entry behaves as today.

## Measured / to measure before W1161

- That `git hook run pre-commit` in the snapshot sees an index equal to the tree (the hook's
  worktree-equals-index precondition).
- That the verdict's sha7 per commit is stable after the real-index refresh.
