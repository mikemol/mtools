# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The git-tracked file names of a workspace, for BUILD files that name every input (mtools:W799).

Operator 2026-10-06: a gate's inputs are named files, never a glob and never a directory. Naming them
by hand drifts from the tree, so this asks git instead of the filesystem and names them for you:

    # MODULE.bazel
    tracked = use_repo_rule("@mikemol_rules_py//:tracked.bzl", "tracked_files")
    tracked(name = "tracked")

    # BUILD.bazel
    load("@mikemol_rules_py//:tracked.bzl", "select_tracked")
    load("@tracked//:manifest.bzl", "TRACKED")
    py_test(..., data = select_tracked(TRACKED, prefix = "notes/people/", suffix = ".md"))

- The population is `git ls-files -z`, which reads the INDEX: a staged file is in, an untracked file
  is out, whatever the working tree holds. A new tracked file therefore joins the gate by being
  tracked, and an untracked scratch file can never join it.
- Only NAMES cross over. The files stay in the workspace's own package, so a script that finds its
  inputs relative to itself still does (a file pulled in from a second repository lands in a different
  runfiles root and breaks that). `select_tracked` returns plain paths, which are this package's labels.
- A tracked name whose file is gone from the work tree (deleted, not yet staged) is a label that does
  not resolve, so analysis fails naming it, rather than the gate quietly checking less.
- The repository holds no glob() and declares no directory. `rctx.watch` on the git index re-runs
  the rule whenever git's view changes.
- A tracked file inside a subdirectory that has its own BUILD file belongs to that package, and its
  label is not this package's: select a prefix that stays inside one package.
"""

def _tracked_files_impl(rctx):
    root = rctx.workspace_root

    # ⚑ ASK GIT WHERE THE INDEX IS. In a linked worktree `.git` is a pointer file and the index lives
    # under the main repo's .git/worktrees/<name>/, so watching <root>/.git/index would watch nothing.
    gd = rctx.execute(["git", "-C", str(root), "rev-parse", "--absolute-git-dir"], quiet = True)
    if gd.return_code != 0:
        fail("tracked_files: git rev-parse --absolute-git-dir failed in %s: %s" % (root, gd.stderr))
    rctx.watch(rctx.path(gd.stdout.strip() + "/index"))
    res = rctx.execute(["git", "-C", str(root), "ls-files", "-z"], quiet = True)
    if res.return_code != 0:
        fail("tracked_files: git ls-files failed in %s: %s" % (root, res.stderr))
    paths = sorted([p for p in res.stdout.split("\0") if p])
    rctx.file("manifest.bzl", "TRACKED = [\n" + "".join(["    %s,\n" % repr(p) for p in paths]) + "]\n")
    rctx.file("BUILD.bazel", "")

tracked_files = repository_rule(
    implementation = _tracked_files_impl,
    doc = "The git-tracked file names of this workspace (from the index), as @<name>//:manifest.bzl's TRACKED.",
    local = True,
)

def select_tracked(tracked, prefix = "", suffix = "", exclude = []):
    """The tracked files under `prefix` ending in `suffix`, as plain paths, named one by one.

    Args:
        tracked: the TRACKED list loaded from the repository's manifest.bzl.
        prefix: only paths starting with this (a path prefix, not a directory input).
        suffix: only paths ending with this.
        exclude: exact paths to leave out.

    Returns:
        The matching paths, in index order. Fails when nothing matches: an empty input set is a
        broken selector, never a clean gate.
    """
    out = [p for p in tracked if p.startswith(prefix) and p.endswith(suffix) and p not in exclude]
    if not out:
        fail("select_tracked: no tracked file matches prefix=%r suffix=%r" % (prefix, suffix))
    return out
