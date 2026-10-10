<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# Installing mtools distributions

Each top-level directory with a `pyproject.toml` is its own distribution. There are 28 of them, listed
below. The repository root has a `pyproject.toml` too, but it carries no `[project]` table: the root is
not a distribution. A repository that adopts one installs it from git by subdirectory:

```console
$ uv add "mikemol-hooks @ git+https://github.com/mikemol/mtools.git@<sha>#subdirectory=hooks"
```

## The distributions

Each entry is `directory`, the distribution name, and the console scripts it installs. A distribution
with no scripts is a library that other distributions import.

- `atomicwrite` (`mikemol-atomicwrite`): durable file writes. A library, no scripts.
- `audiostruct` (`mikemol-audiostruct`): transcription and diarization read losslessly. Script:
  `mikemol-audio`.
- `bibparse` (`mikemol-bibparse`): a strict parser for paperkit's bib grammar. A library, no scripts.
- `buildtel` (`mikemol-buildtel`): build telemetry. Scripts: `mikemol-coord-sample`, `mikemol-logs-push`,
  `mikemol-image-digest`.
- `corpus` (`mikemol-corpus`): which Python files are a tree's corpus. A library, no scripts.
- `fence` (`mikemol-fence`): run a command inside a cgroup and report what it consumed. Scripts:
  `mikemol-fence`, `mikemol-membudget`.
- `gatecheck` (`mikemol-gatecheck`): pre-commit and gate helpers. Scripts: `mikemol-hook-index`,
  `mikemol-hook-grid`, `mikemol-absence-audit`, `mikemol-lint-bzl`, `mikemol-witness-reach`.
- `gmailstruct` (`mikemol-gmailstruct`): Gmail API message JSON read losslessly. Script: `mikemol-gmail`.
- `grade` (`mikemol-grade`): the falsifiability grade ladder. A library, no scripts.
- `gradekit` (`mikemol-gradekit`): grade records and the effective-grade clamp. Scripts:
  `mikemol-gradekit-verdict`, `mikemol-grades-rec`, `mikemol-read-grade`, `mikemol-effective`.
- `hooks` (`mikemol-hooks`): Claude Code hooks, plus a few maintainer tools. Scripts:
  `mikemol-hook-structural-query`, `mikemol-hook-no-chaining`, `mikemol-hook-no-verify`,
  `mikemol-hook-shellcheck`, `mikemol-hook-pycheck`, `mikemol-hook-inbound-asks`,
  `mikemol-hook-nemik-check`, `mikemol-gate-ledger`, `mikemol-shellcheck`, `mikemol-gen-warrants`,
  `mikemol-githook-pre-push`.
- `htmlstruct` (`mikemol-htmlstruct`): Read HTML and MHTML documents as structure. Scripts: `mikemol-htmlstruct`.
- `icsstruct` (`mikemol-icsstruct`): iCalendar read losslessly. Script: `mikemol-ics`.
- `importdag` (`mikemol-importdag`): a project's import DAG. Scripts: `mikemol-dagnames`,
  `mikemol-closure-census`, `mikemol-closure`, `mikemol-imports`, `mikemol-dagbzl`.
- `ledger` (`mikemol-ledger`): a findings ledger whose rows are witnessed by commands. A library, no
  scripts.
- `mdstruct` (`mikemol-mdstruct`): structural reading and writing of markdown. Script: `mdstruct`.
- `memres` (`mikemol-memres`): memory reservation tools. Scripts: `mikemol-mem-project`,
  `mikemol-mem-harvest`, `mikemol-sweep-budget`, `mikemol-cpuweight`.
- `mutantcell` (`mikemol-mutantcell`): the def-sweep's cell. Scripts: `mikemol-eval`, `mikemol-sites`.
- `mutation` (`mikemol-mutation`): mutation primitives. Script: `mikemol-mutate`.
- `pathsforward` (`mikemol-pathsforward`): the paths-forward loop's state file and its reader and writer.
  Script: `mikemol-paths-forward`.
- `pathwalk` (`mikemol-pathwalk`): expand directory operands to their Python files. A library, no scripts.
- `pkgbuild` (`mikemol-pkgbuild`): Bazel packaging actions. Scripts: `mikemol-wheel`, `mikemol-pyc`,
  `mikemol-pyinfo`.
- `pycodemod` (`mikemol-pycodemod`): structural queries over Python source. Script: `mikemol-pycodemod`.
- `pytestspec` (`mikemol-pytestspec`): a pytest plugin that collects Rego specs. A library, no scripts.
- `ratchet` (`mikemol-ratchet`): a paydown-only ratchet over a baseline set. Script: `mikemol-ratchet`.
- `transcriptstruct` (`mikemol-transcriptstruct`): Claude Code transcripts read losslessly. Script:
  `mikemol-transcriptstruct`.
- `treeio` (`mikemol-treeio`): one read/write seam over a working tree and git history. Scripts:
  `mikemol-vfs`, `mikemol-edit-snapshot`.
- `witness` (`mikemol-witness`): the witness contract. A library, no scripts.

The package list comes from each directory's `pyproject.toml`, which is also what the gate's `_dists`
glob (`*/pyproject.toml`) reads. `rules_py` is the root of its own bazel module and is not a distribution.
Some distributions depend on siblings (`gradekit` on `grade`, `bibparse` and `atomicwrite`; `importdag`
on `atomicwrite`; `mdstruct` and `pycodemod` on `pathwalk`; `mutantcell` on `mutation` and `importdag`;
`gatecheck` on `importdag`). Those links are `path` sources in each `pyproject.toml`, so check the
distribution you take before assuming it resolves alone from git.

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

## Hooks and pathsforward go together

The two context hooks in `mikemol-hooks`, `mikemol-hook-inbound-asks` and `mikemol-hook-nemik-check`,
read a paths-forward queue. `mikemol-hook-inbound-asks` runs `mikemol-paths-forward`, which looks first
in the adopting repo's own `.venv/bin`. The `mikemol-hooks` wheel does not declare `mikemol-pathsforward`
as a dependency, so a repo taking the hook names both, at the same sha:

```toml
[project]
dependencies = [
    "mikemol-hooks @ git+https://github.com/mikemol/mtools.git@<sha>#subdirectory=hooks",
    "mikemol-pathsforward @ git+https://github.com/mikemol/mtools.git@<sha>#subdirectory=pathsforward",
]
```

`<sha>` is one commit, the same in both specs. The hook is wired in the adopting repo's
`.claude/settings.json`; see [adopting a hook](docs/adopting-a-hook.md) for the three shapes and the
exact blocks.

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
