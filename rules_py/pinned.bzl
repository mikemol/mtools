# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A sibling repo at a recorded commit, its files named one by one (mtools:W843, design W797/W798).

A gate that reads `~/github/paperkit` reads whatever that working tree holds today: a dirty or moved
sibling changes the verdict and nothing says so. This gives the gate the repo AT A COMMIT instead:

    # MODULE.bazel
    pinned = use_repo_rule("@mikemol_rules_py//:pinned.bzl", "pinned_files")
    pinned(name = "paperkit_engine", remote = "/home/mikemol/github/paperkit",
           commit = "<sha>", prefix = "paperkit/")

    # BUILD.bazel
    load("@mikemol_rules_py//:pinned.bzl", "pinned_labels")
    load("@paperkit_engine//:manifest.bzl", "FILES")
    py_test(..., data = pinned_labels("paperkit_engine", FILES))

- The files come from `git archive <commit>`, so the working tree of `remote` is never read: only
  its object database is. A commit the clone does not hold fails the fetch, naming it.
- The names come from `git ls-tree -r <commit>`, never a glob and never a directory (operator
  2026-10-06). `prefix` keeps only the paths under it, and the repository fails when none match: an
  empty input set is a broken selector, never a clean gate.
- The sibling's own BUILD, WORKSPACE and MODULE files are deleted from the extracted tree: they
  would make subdirectories packages of their own and unname the files beside them.
- The repository is not `local`: its content is a function of `remote` and `commit` alone, so a
  moved working tree cannot change it, and a cache hit is sound.
- Each file is exported by name from the repository's root package, at the same relative path it has
  in the sibling repo (`@paperkit_engine//:paperkit/gate.py`), so a script that finds its siblings
  relative to itself still does.
"""

def _pinned_files_impl(rctx):
    remote = rctx.attr.remote
    commit = rctx.attr.commit
    if len(commit) != 40 or not all([c in "0123456789abcdef" for c in commit.elems()]):
        fail("pinned_files: commit must be a full 40-hex sha, got %r (a ref moves; a sha does not)" % commit)
    listing = rctx.execute(["git", "-C", remote, "ls-tree", "-r", "-z", "--name-only", commit], quiet = True)
    if listing.return_code != 0:
        fail("pinned_files: %s does not hold commit %s: %s" % (remote, commit, listing.stderr))
    everything = [p for p in listing.stdout.split("\0") if p]

    # ⚑ THE SIBLING'S OWN BUILD FILES ARE DELETED, NOT EXPORTED. A BUILD.bazel under the prefix turns
    # its directory into a subpackage, so the files beside it stop being labels of the root package
    # (`paperkit/BUILD.bazel` made `@paperkit_engine//:paperkit/gate.py` invalid). They describe the
    # sibling's own build, which this gate does not run.
    own_builds = [p for p in everything if p.split("/")[-1] in ("BUILD", "BUILD.bazel", "WORKSPACE", "WORKSPACE.bazel", "MODULE.bazel")]
    names = sorted([p for p in everything if p.startswith(rctx.attr.prefix) and p not in own_builds])
    if not names:
        fail("pinned_files: no path of %s at %s starts with %r" % (remote, commit, rctx.attr.prefix))
    archive = rctx.execute(["git", "-C", remote, "archive", "--format=tar", "-o", str(rctx.path("pinned.tar")), commit], quiet = True)
    if archive.return_code != 0:
        fail("pinned_files: git archive %s failed: %s" % (commit, archive.stderr))
    rctx.extract("pinned.tar")
    rctx.delete("pinned.tar")
    for p in own_builds:
        rctx.delete(p)
    rctx.file("manifest.bzl", "FILES = [\n" + "".join(["    %s,\n" % repr(p) for p in names]) + "]\n")
    rctx.file("BUILD.bazel", "exports_files([\n" + "".join(["    %s,\n" % repr(p) for p in names]) + "])\n")

pinned_files = repository_rule(
    implementation = _pinned_files_impl,
    attrs = {
        "commit": attr.string(mandatory = True, doc = "the full 40-hex sha to read"),
        "prefix": attr.string(default = "", doc = "keep only the paths under this prefix"),
        "remote": attr.string(mandatory = True, doc = "the local clone whose object database holds the commit"),
    },
    doc = "A sibling repo's files at a commit, each named, never read from its working tree.",
)

def pinned_labels(repo, files, prefix = ""):
    """The files under `prefix` as labels of a pinned repository's root package.

    Args:
        repo: the repository's name, as MODULE.bazel gave it (`paperkit_engine`).
        files: the FILES list loaded from that repository's manifest.bzl.
        prefix: only paths starting with this.

    Returns:
        The labels, one per file. Fails when nothing matches: an empty input set is a broken
        selector, never a clean gate.
    """
    out = ["@%s//:%s" % (repo, p) for p in files if p.startswith(prefix)]
    if not out:
        fail("pinned_labels: no pinned file of %s starts with %r" % (repo, prefix))
    return out
