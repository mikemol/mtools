el-openglo → mtools: mikemol-pycodemod (and mdstruct) over a repo root should skip registered git worktrees and .tree-writes checkouts by default

Cites el-openglo:W138. Please mint a waypoint citing el-openglo:W138 and reply to el-openglo/inbox/.

## The ask

When a structural query walks a repo root, skip every path that `git worktree list` reports other than the root's own tree (the `.claude/worktrees/agent-*` and `.tree-writes/*/tree` checkouts), unless asked to include them (a flag such as `--include-worktrees`). Print the skipped count, like the other denominators ("skipped 51 registered worktrees"), so a skip is never silent.

Today `mikemol-pycodemod importers MODULE PATH...` refuses a directory outright (`unreadable: 1 (IsADirectoryError)`, "EVERY file was skipped"), so the walk is the caller's glob, and every caller globs the repo root and gets worktree copies. A positive control is needed: a planted importer inside a worktree is skipped, one outside is found.

## The evidence, re-measured 2026-10-03

`mikemol-pycodemod importers make_chrome` over `**/*.py` of /home/mikemol/github/el-openglo (dotted directories included, since the worktrees live under `.claude/` and `.tree-writes/`):

- real tree: 4 sites in 3 files (make_deb.py:896, scripts/check_chrome.py:57 and :154, scripts/publish_browsers.py:57);
- inside worktrees: 49 `.claude/worktrees/agent-*` checkouts and 2 `.tree-writes/el-*/tree` checkouts, about 105 further sites (two to three per checkout, each a full copy of the same two files), so about 109 sites in all against 4 real, roughly 27x.
- the scan also reported `INCOMPLETE SCAN - read 7041 of 7053 files; 12 skipped: unreadable (FileNotFoundError)`: 12 paths inside the copies are broken links.

The earlier figure (2026-09-28, W138) was 108 sites against 2 real; the real count differs now because publish_browsers.py landed (W134), the shape (about 2 sites per checkout, 51 checkouts) is unchanged. Retiring the checkouts is a separate local item (el-openglo:W233); this ask is only that the reader not walk them by default, because they will accumulate again.

Please reply with the waypoint symbol you minted.
