# Upstream filing for patches/rules_python-uv-lock-git-kind.patch — DRAFTS, not yet posted

Target: https://github.com/bazel-contrib/rules_python/issues/4139 (open, 2026-09-02).
Prior: #4084 (closed 2026-08-22) fixed the repo-name half; #4139 is the download-URL half.
Operator ruling 2026-09-20: post comment + PR after reading these.

---

## Comment on #4139

I hit this on 2.3.3 with a `uv.lock` carrying a git-sourced dev dependency, and measured two
things that may save the next reader some time.

**The `simpleapi_skip` workaround does not reach the pip path for a git source.** With the
package listed in `simpleapi_skip`, the fetch fails identically:

```
wheel_installer --requirement paperkit==0.1.0 … --extra_pip_args '["--find-links", "."]'
ERROR: No matching distribution found for paperkit==0.1.0
```

Reading why: `simpleapi_skip` only sets `use_downloader = False`
(`hub_builder.bzl:370`). The pip-installed fallback at `hub_builder.bzl:649` is gated on
`if not src.url`, and a git source always carries its URL, so the downloader branch is
taken regardless and bazel fetches the repository's web page as a file named after the
package. Even if the fallback were reached, `_parse_uv_lock_json` emits
`requirement_line = "{name}=={version}"` for every kind (`parse_requirements.bzl:278`),
so pip would still be asked an index for a version that exists only in a repository.

**Two small changes make it work.** For a git source: (1) emit the direct-reference form
`name @ git+<url>@<rev>` — the same line `uv pip compile` writes for the same lock, which
pip resolves natively; (2) leave `url` empty so the pip-installed path is taken. The revision
after `#` in `uv.lock` is the resolved commit; a `?rev=` query is the request that fragment
answers, so it is dropped rather than duplicated.

Applied as a `single_version_override` patch in our tree, the package builds from git and the
resulting venv matches what `uv sync` produces on the host (same transitive versions —
that divergence was the reason we moved to `uv_lock` in the first place). PR to follow.

---

## PR

**Title:** pypi: uv.lock git sources reach pip as a direct reference (fixes #4139)

**Body:**

Fixes #4139.

A package with `source = { git = "…#<rev>" }` in `uv.lock` currently fails to fetch.
`_parse_uv_lock_json` builds a `git_struct` with `kind = "git"` and then:

- emits `requirement_line = "{name}=={version}"` regardless of kind, and
- carries the git URL in `url`, so `hub_builder` skips the pip-installed fallback
  (`if not src.url`) and hands the URL to bazel's downloader, which fetches the
  repository's HTML page as a file.

pip is then asked for `name==version` from `--find-links .` and finds nothing. The
`simpleapi_skip` workaround suggested on the issue does not change either step (it only
sets `use_downloader = False`; the fallback gate is on `url`).

This change makes a git source emit `name @ git+<url>@<rev>` — the form `uv pip compile`
writes for the same lock — and leaves `url` empty so the existing pip path builds it. The
revision fragment is the resolved commit; a `?rev=` query is dropped as redundant.

Measured on 2.3.3 with a git-sourced dev dependency: before, `No matching distribution
found for paperkit==0.1.0`; after, the package is built from git and the hub's closure
matches `uv sync`'s on the host.

Regression test: `tests/pypi/parse_requirements/parse_requirements_tests.bzl` — a uv.lock
fixture with a git source, asserting the resolved `requirement_line` is the direct
reference and `url` is empty. (TO WRITE on the fork branch before opening.)

---

## Checklist before posting

- [ ] Operator has read both texts above.
- [ ] Fork bazel-contrib/rules_python under the operator's account (`gh repo fork`).
- [ ] Branch `uv-lock-git-direct-ref`; apply the patch; add the regression test; run the
      repo's own test for parse_requirements.
- [ ] Post the comment; open the PR; record both URLs in the patch header and W10.
