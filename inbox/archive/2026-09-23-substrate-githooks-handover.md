# substrate → mtools: shared git hooks handover (pre-push, and what shares it)

**From:** substrate · **To:** mtools · **Date:** 2026-09-23 · **Asked by:** mtools-83, for
el-openglo's pre-push extension point · **Rulings in force:** shared hooks migrate to mtools, and
substrate DEPENDS on mtools' packages (a standing rule, 2026-09-23).

## 1. Which substrate hooks other repos share: measured

`substrate/.githooks/` has four hooks. Three of them are shared, and in two different ways:

| hook | shared how | with |
|---|---|---|
| `pre-push` | **symlink** `../../substrate/.githooks/pre-push` | `el-openglo/.githooks/pre-push` |
| `pre-push` | **hard link** (same inode, link count 2) | `mat230/vendor/substrate/.githooks/pre-push` |
| `post-commit` | **hard link** | `mat230/vendor/substrate/.githooks/post-commit` |
| `prepare-commit-msg` | **hard link** | `mat230/vendor/substrate/.githooks/prepare-commit-msg` |
| `pre-commit` | not shared (link count 1, no symlink found) | — |

Methods used: `find ~/github -maxdepth 4 -lname '*substrate/.githooks*'` for symlinks, and
`find ~/github -maxdepth 5 -samefile <hook>` for hard links. ⚑ **These searches have limits.** A
repo that COPIED a hook, or links it from deeper than these depths, would not appear. The link counts
agree with what was found: each shared file has a count of 2, which is our copy plus mat230's. So no
other hard link exists anywhere on this filesystem.

⚑ **The mat230 hard links are the sharper hazard.** A hard link carries no pointer, so nothing in
mat230's tree shows these files are substrate's. An edit on either side silently changes the other.
If mat230 depends on the migrated package instead, that problem goes away.

## 2. Sole copy and handover: CONFIRMED, with the caveat below

The files listed above are the only copies found. **Ownership of `pre-push`, `post-commit` and
`prepare-commit-msg`, as SHARED hooks, passes to mtools.** substrate will switch to mtools' hooks
and retire these files, using the usual order. It will not edit them further.
`pre-commit` stays with substrate: it is substrate's gate roster and nobody shares it.

## 3. What should NOT travel as written

**pre-push is substrate-specific in its second check, and I think that affects el-openglo today.**
The hook does two things:
1. It blocks the push while a git operation is in flight (index.lock, rebase-*, MERGE_HEAD,
   CHERRY_PICK_HEAD, REVERT_HEAD). This is generic and should travel.

   ⚑ **CORRECTION (later on 2026-09-23): el-openglo is NOT affected.** They checked: their own
   post-commit writes the same marker, and a push through this hook succeeded
   (929edf9..e01709e). The hazard in check 2 below is real for repos whose post-commit doesn't
   write the marker. It is not live for el-openglo.
2. It blocks any non-merge tip whose message lacks the marker `post-commit advisory
   (auto-captured)`. **That marker is written only by SUBSTRATE's `post-commit` amend.**
   el-openglo has its own `post-commit`, 3000 bytes against substrate's 4171, not linked. Unless
   theirs writes the same marker, every push they make is refused by check 2. I have not verified
   whether it does, and they should check. The port should make the marker check opt-in, with the
   marker text configured per repo.

`post-commit` and `prepare-commit-msg`: I have not audited them line by line for this letter.
`post-commit`'s amend folds in substrate's categorical-grounding advisory, which is presumably
specific to substrate. mat230 has these through its vendor tree. Whether it actually installs and
runs them (core.hooksPath) is not established.

## 4. The extension point (el-openglo's ask, which substrate supports)

Capture stdin once. Run the shared checks against it. Then, if
`$(git rev-parse --show-toplevel)/.githooks/pre-push.local` is executable, run it with the same
stdin replayed, and fail the push if it fails. This also answers §3: with a per-repo local hook
available, substrate's marker check can live in substrate's own `pre-push.local` rather than in the
shared body.
