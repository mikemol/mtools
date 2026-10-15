<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# Installing mtools distributions

Each top-level directory with a `pyproject.toml` is its own distribution. There are 34 of them, listed
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
- `buildtel` (`mikemol-buildtel`): build telemetry. Scripts: `mikemol-buildlog`,
  `mikemol-coord-sample`, `mikemol-logs-push`, `mikemol-image-digest`.
- `corpus` (`mikemol-corpus`): which Python files are a tree's corpus. A library, no scripts.
- `debtplan` (`mikemol-debtplan`): plan the pay-down of a per-file debt ledger: leaves first, direct
  waits only, a cycle refused rather than blocked on. Script: `mikemol-debtplan`.
- `fence` (`mikemol-fence`): run a command inside a cgroup and report what it consumed. Scripts:
  `mikemol-fence`, `mikemol-membudget`.
- `frontier` (`mikemol-frontier`): Pure frontier walk over plain nodes and edges: ready, deferred with the unmet predecessor or gate, realized, and a named cycle A library, no scripts.
- `gatecheck` (`mikemol-gatecheck`): pre-commit and gate helpers. Scripts: `mikemol-hook-index`,
  `mikemol-hook-grid`, `mikemol-absence-audit`, `mikemol-lint-bzl`, `mikemol-witness-reach`.
- `gmailstruct` (`mikemol-gmailstruct`): Gmail API message JSON read losslessly. Script: `mikemol-gmail`.
- `grade` (`mikemol-grade`): the falsifiability grade ladder. A library, no scripts.
- `gradekit` (`mikemol-gradekit`): grade records and the effective-grade clamp. Scripts:
  `mikemol-gradekit-verdict`, `mikemol-grades-rec`, `mikemol-read-grade`, `mikemol-effective`.
- `hooks` (`mikemol-hooks`): Claude Code hooks, git hooks and maintainer tools. Scripts:
  `mikemol-bazel-admit`, `mikemol-build-failure`, `mikemol-commit`, `mikemol-gate-jobs`,
  `mikemol-gate-ledger`, `mikemol-gen-warrants`, `mikemol-githook-post-commit`,
  `mikemol-githook-pre-push`, `mikemol-githook-prepare-commit-msg`, `mikemol-hook-after-compaction`,
  `mikemol-hook-build-failure`, `mikemol-hook-inbound-asks`, `mikemol-hook-nemik-check`,
  `mikemol-hook-no-chaining`, `mikemol-hook-no-verify`, `mikemol-hook-pycheck`,
  `mikemol-hook-pycheck-advise`, `mikemol-hook-read-guard`, `mikemol-hook-shellcheck`,
  `mikemol-hook-structural-query`, `mikemol-hook-tick-gate`, `mikemol-hook-tick-release`,
  `mikemol-hook-tick-stop`, `mikemol-hook-work-claims`, `mikemol-hooks-probe`, `mikemol-new-dist`,
  `mikemol-privacy-audit`, `mikemol-privacy-shipped`, `mikemol-pycheck`, `mikemol-repin`,
  `mikemol-shellcheck`, `mikemol-snapshot`, `mikemol-vlog`, `mikemol-wheel`.
- `htmlstruct` (`mikemol-htmlstruct`): Read HTML and MHTML documents as structure. Scripts: `mikemol-htmlstruct`.
- `icsstruct` (`mikemol-icsstruct`): iCalendar read losslessly. Script: `mikemol-ics`.
- `importdag` (`mikemol-importdag`): a project's import DAG. Scripts: `mikemol-dagnames`,
  `mikemol-closure-census`, `mikemol-closure`, `mikemol-imports`, `mikemol-dagbzl`.
- `katas` (`mikemol-katas`): the host orchestration katas: workstream discovery and the detached
  commit's bookkeeping. Script: `mikemol-katas`.
- `ledger` (`mikemol-ledger`): a findings ledger whose rows are witnessed by commands. A library, no
  scripts.
- `mdstruct` (`mikemol-mdstruct`): structural reading and writing of markdown. Script: `mdstruct`.
- `memres` (`mikemol-memres`): memory reservation tools. Scripts: `mikemol-mem-project`,
  `mikemol-mem-harvest`, `mikemol-sweep-budget`, `mikemol-cpuweight`, `mikemol-cpu-census`,
  `mikemol-rail`.
- `mutantcell` (`mikemol-mutantcell`): the def-sweep's cell. Scripts: `mikemol-eval`, `mikemol-sites`.
- `mutation` (`mikemol-mutation`): mutation primitives. Script: `mikemol-mutate`.
- `pathsforward` (`mikemol-pathsforward`): the paths-forward loop's state file and its reader and writer.
  Script: `mikemol-paths-forward`.
- `pathwalk` (`mikemol-pathwalk`): expand directory operands to their Python files. A library, no scripts.
- `pkgbuild` (`mikemol-pkgbuild`): Bazel packaging actions. Scripts: `mikemol-wheel`, `mikemol-pyc`,
  `mikemol-pyinfo`.
- `procrun` (`mikemol-procrun`): start a child process in one place: argv never a shell, output
  captured as text, a non-zero status a value. A library, no scripts.
- `pycodemod` (`mikemol-pycodemod`): structural queries over Python source. Script: `mikemol-pycodemod`.
- `pytestspec` (`mikemol-pytestspec`): a pytest plugin that collects Rego specs. A library, no scripts.
- `ratchet` (`mikemol-ratchet`): a paydown-only ratchet over a baseline set. Script: `mikemol-ratchet`.
- `rulerseq` (`mikemol-rulerseq`): Ruler-sequence table rules: the 2-adic valuation of a row boundary rendered as a Morse motif, so a rule's pattern carries a row enumeration's binary structure (WCAG 1.4.1). A library, no scripts.
- `transcriptstruct` (`mikemol-transcriptstruct`): Claude Code transcripts read losslessly. Script:
  `mikemol-transcriptstruct`.
- `treeio` (`mikemol-treeio`): one read/write seam over a working tree and git history. Scripts:
  `mikemol-vfs`, `mikemol-edit-snapshot`.
- `waldo` (`mikemol-waldo`): Waldo: a narrow tool that holds one privilege and does only a declared action, with a declared allowed set, refuse-with-diff, same-plan apply and witnesses. A library, no scripts.
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
