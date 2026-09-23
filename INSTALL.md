<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# Installing mtools distributions

Each top-level directory with a `pyproject.toml` (`hooks`, `mdstruct`, `fence`, `ratchet`,
`pathsforward`) is its own distribution. A repository that adopts one installs it from git by subdirectory:

```console
$ uv add "mikemol-hooks @ git+https://github.com/mikemol/mtools.git@<sha>#subdirectory=hooks"
```

## Pin a commit sha, not `@main`, when you take more than one

**Two `@main` specs in one uv project resolve to ONE commit, and it may be the wrong one.**
substrate measured this on 2026-09-22 with two specs, `…mtools.git@main#subdirectory=hooks` and
`…@main#subdirectory=mdstruct`. uv resolved `@main` once, to the commit already recorded in the
lock for mdstruct (`536442d`), and used that commit for hooks too, while `git ls-remote` showed
`main` at `e9f220a`. Neither `--upgrade-package` nor `--refresh-package` moved it. **Only a sha pin
did.**

So an adopter taking two or more mtools distributions names the same sha in each spec:

```toml
[project]
dependencies = [
    "mikemol-hooks @ git+https://github.com/mikemol/mtools.git@e85ba31d4bfd8634d4afe8c498348db7727c382a#subdirectory=hooks",
    "mikemol-mdstruct @ git+https://github.com/mikemol/mtools.git@e85ba31d4bfd8634d4afe8c498348db7727c382a#subdirectory=mdstruct",
]
```

## With an environment marker

A direct reference takes a PEP 508 marker after the URL, **separated by a space before the `;`**.
PEP 508 requires that whitespace, because `;` is a legal character inside a URL. summit measured
this form on 2026-09-23: `uv lock` accepted it and recorded it byte-identically to the
`[tool.uv.sources]` spelling it replaced.

```toml
"mikemol-hooks @ git+https://github.com/mikemol/mtools.git@<sha>#subdirectory=hooks ; python_full_version >= '3.13'"
```

## One sha across every spec

One sha across all specs is what you want anyway: the distributions are developed and gated
together, so a set taken from one commit is a set that passed one gate. Move the pin by editing
every spec to one new sha.

## Why a PEP 508 direct reference and not `[tool.uv.sources]`

`[tool.uv.sources]` is uv-only and is **dropped from wheel metadata**, so a package that depends on
yours would inherit a bare name its resolver cannot satisfy. A direct reference in
`dependencies` travels with the metadata.
