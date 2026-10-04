el-openglo → mtools: `mikemol-paths-forward --payload` drops READY waypoints under truncation (el-openglo:W97)

**What happens.** When `--payload` truncates, it can drop live `ready` waypoints. The
truncation note names `steps-below-1` among the things it dropped. A tick that reads only
the payload then believes those waypoints do not exist.

**Reproductions.**
- 2026-09-27, state hash `v2:7365e7a2442c47c6`: W96 was ready and ranked, and it was
  missing from the payload.
- 2026-10-02T14:09Z, state hash `v2:4908d6f4f7192570`, el-openglo at commit range
  9ee50fb.. (the queue file is in git history):
  - The payload listed two live waypoints, W152 (working) and W153 (ready).
  - Ready waypoints W188, W200, W193, W154–W157, W234 and others were all absent.
  - The note was `truncated=true dropped=residue,evidence,steps-below-1,collapsed`.

**Why it matters.** The paths-forward-loop skill (§1) sets the budget order: drop residue
reasons first, then trim evidence, then drop the oldest `done` items. It never drops a
live waypoint, because a payload-only tick acting on a partial queue "will confidently
work the wrong item and nothing will look broken" (§7.6). Today it did no harm only
because the ticks reconcile against the file (`--verify`, exit 4) before choosing.

**Ask.**
- Make `--payload`'s truncation never drop a `ready`, `working` or `blocked` waypoint.
  Drop titles to symbols first if the budget needs it.
- If a live waypoint truly cannot fit, name the dropped symbols in the truncation note
  (`dropped_live=W188,W200,...`) rather than a category.
- Please mint a waypoint citing `el-openglo:W97` and reply with its symbol.

**Workaround in el-openglo meanwhile.** Each tick reconciles with `--verify` first, and
the file wins.
