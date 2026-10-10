# W891: commit in a private index, gated on the tree that lands (2026-10-09)

Problem (measured by luthen-observability:W684, two live sessions). `mikemol-commit` runs
`git commit -- <paths>`, an `--only` commit: git takes `.git/index.lock` for the WHOLE run, hooks
included, so a peer's `git add` fails for the minutes the gate takes. And the gate's
worktree-equals-index precondition (gatecheck.hook_index, the `differs from the index` check)
refuses on ANOTHER session's unstaged files, so neither session can commit alone.

Both are one defect: the gate runs on the shared working tree and the shared index. The precondition
exists because "the hook gates the WORKING TREE; a commit lands the INDEX, and the two diverge"
(hook_index docstring). The principled fix removes the divergence instead of policing it: gate the
tree that lands.

## Mechanism (small, because git already has the pieces)

1. **The commit's tree**: a private index `GIT_INDEX_FILE=<git-dir>/mtools/commit.index`, filled by
   `git read-tree HEAD` then `git add -A -- <paths>` (a deleted path is a deletion; `-A` covers it),
   then `git write-tree`.
2. **The snapshot**: `mikemol-snapshot` (W845, built) materializes that tree at its FIXED namespaced
   path under flock; the fixed path is what keeps bazel's output base warm (operator ruling
   2026-10-06), which answers hook_index's "a second workspace costs a cold cache".
3. **The commit**: `git commit -F msg` run with `GIT_DIR=<real .git>`, `GIT_WORK_TREE=<snapshot>`,
   `GIT_INDEX_FILE=<private index>`, cwd = the snapshot. Git runs the repo's own hooks unchanged
   (pre-commit, commit-msg, post-commit), and from their point of view the worktree IS the index, so
   hook_index passes by construction. HEAD of the real repository moves; the real `.git/index` and
   its lock are never touched during the run.
4. **The sync**: afterwards, `git reset -q -- <paths>` on the real index (a momentary lock) so the
   committed paths read as committed, not as a staged reversal.

## Slices

| card | what |
| --- | --- |
| W901 | the experiment as a test, on real git repos: with the three env vars and cwd = snapshot, the hooks run, HEAD moves, `.git/index.lock` never exists during the hook, the real worktree is untouched, and a peer's unstaged file does not refuse. |
| W902 | `commit_kata`: `isolated` mode builds the private index (step 1) and runs step 3; a `MIKEMOL_COMMIT_ISOLATED=1` opt-in first, default after a soak. |
| W903 | the real-index sync (step 4) and the staged-deletion case (the luthen bug class), with tests. |
| W904 | adopt in mtools after soak: flip the default, tell luthen-observability (W684) and the peers by letter. |

## Open (decided here, revisit on evidence)

- `post-commit` pushes with the hook env inherited; it uses `git rev-parse --git-dir`, which is the
  real `.git`, so the witness file and the push are unchanged. W901 asserts it.
- A repo whose gate cannot run from a snapshot path (absolute paths baked in) keeps today's mode:
  isolation is opt-in per repo until proven.
