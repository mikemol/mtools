# Splitting mtools into one repository per dist (design, not started)

Status: DESIGN ONLY. Nothing moves, nothing is published, until the operator green-lights it.
Cards: W1219 (billing facts), W1220-W1222 (layout mapping, landed or landing), W1223 (this note),
W1224 (pin inventory), W1225 (history rehearsal), W1226 (gate and release workflow options).
Parent goal: W1143. Held: W1153 (the 68 pending-publisher forms are not filed against
`mikemol/mtools`; the values change per dist when each moves).

## This note is an ADDENDUM to an existing, operator-ruled plan (read 2026-10-15)

W317 ("Plan splitting mtools into a GitHub org with one repo per distribution") and
`.claude/design/W317-split-plan.md` already exist, with the operator's 2026-10-01 rulings, read
from W317's evidence: org `mikemol-tools` (created 2026-10-01, free plan, 0 public repos); each repo
keeps its history (`git filter-repo` per subdirectory); mtools stays as the workstream repo; shared
machinery becomes its own atomic modules (W321, the five check atoms W323-W327 are done); per-repo
gates on GitHub Actions ("free for public repos", consistent with the billing facts below); a
reusable workflow `mikemol-tools/workflows/.github/workflows/module-gate.yml` (a draft at
`ci/module-gate.yml`, not wired) on a self-hosted runner luthen-observability maintains (W319,
luthen W257); PyPI with TestPyPI staging via Trusted Publishing (decision D5); the first push is
the icsstruct pilot and "needs the operator's go to push". W317, W319, W504 are operator-held or
blocked on luthen-observability:W257 and are not to be lifted from here.

So this note does not re-plan the split. It adds what the PyPI goal (W1143) needs from it:
the per-repo pending-publisher values (W1220-W1222, done), the pin inventory (below), the history
rehearsal (below), and the billing facts. Nothing here moves anything.

## What the operator asked (relayed by github-8f, 2026-10-14)

Convert mtools into a GitHub organization with each distribution its own repository, to cut the
cost of Actions. The organization exists: `mikemol-tools` (created 2026-10-01, free plan, 0 public
repositories; read with `gh api`, nothing written).

## Billing facts (W1219)

Read 2026-10-14 from docs.github.com/en/billing/managing-billing-for-your-products/
managing-billing-for-github-actions/about-billing-for-github-actions:

- VERIFIED (page text): "GitHub Actions usage is free for self-hosted runners and for public
  repositories that use standard GitHub-hosted runners."
- VERIFIED: GitHub Free allows 2,000 minutes per month for PRIVATE repositories, 500 MB artifact
  storage, 10 GB cache per repository; the page draws no difference for an organization on Free.
- So the cost argument turns on visibility, not on the organization: a public repository on a
  standard runner is already free in a personal account. An organization adds no free minutes
  for public repositories that the personal account lacked.
- VERIFIED (`gh api repos/mikemol/mtools`, 2026-10-14): mikemol/mtools is PUBLIC, so its standard
  runner minutes are already free under that rule; a split to public repositories would not lower
  that cost, and only a PRIVATE repository would use the 2,000-minute allowance.
- The self-hosted charge the operator recalls (read 2026-10-14 at
  github.blog/changelog/2025-12-16-coming-soon-simpler-pricing-and-a-better-experience-for-github-actions/,
  announcement dated 2025-12-16): a $0.002-per-minute "GitHub Actions cloud platform charge" on
  self-hosted runner usage from 2026-03-01, applying to "Jobs that run in private repositories and
  use standard GitHub-hosted or self-hosted runners" (and larger hosted runners); "Standard
  GitHub-hosted or self-hosted runner usage on public repositories will remain free"; GitHub
  Enterprise Server unaffected; the page does not name internal repositories. An update note on
  the same page reads "We're postponing the announced billing change for self-hosted GitHub
  Actions to take time to re-evaluate our approach," with no new date, while the up-to-39%
  hosted-runner price cut still took effect 2026-01-01. (Phrases in quotation marks are the
  fetch tool's rendering of the page; it declined to give the full text, so the exact wording and
  the update note's date are not verified.)
- So, as read: the charge was announced for private repositories only, then postponed, not
  cancelled; one third-party article says "cancelled" and the GitHub page says only "postponed", a
  conflict I leave open. Whether it applies today I could not verify (the billing page I read
  mentions no such charge).
- NOT VERIFIED: the account's actual Actions spend, and whether a replacement pricing has been
  announced since. The cost question stays OPEN; the operator's stated reason for the split is
  organization, not cost.
  The next step before the operator weighs cost is to read the account's actual usage.

## What a split would have to carry (to be filled by W1224, W1225, W1226)

- History per dist (filter), tags, and the shared distributions (gate, hooks, pathsforward) that
  other repositories pin by sha.
- Every sha-pinned git reference to `mikemol/mtools#subdirectory=...` in other repositories (W1224).
- The privacy audit per new repository, including `--history` (W1225).
- One reusable publish workflow in the org versus a copy per repository; one monorepo gate versus
  34 (W1226).
- An order that never breaks a consumer's pin: the old repository keeps resolving every existing
  sha until the last consumer has re-pinned.

## Pin inventory (W1224, first reading)

Instrument: `grep -r -l "mikemol/mtools"` over `/home/mikemol/github` for `pyproject.toml` and
`uv.lock`, skipping `.venv`, `node_modules`, `bazel-mtools`, `.git`. Positive control: it finds
mtools' own dists (below). Denominator: every directory under `~/github` the user can read;
`luthen-observability/.kube` is unreadable and was not searched (so that repository is UNAVAILABLE
for this reading, not absent). Markdown (INSTALL guides) was not searched by this instrument, only
by name.

- Outside repositories whose `pyproject.toml` or `uv.lock` names `mikemol/mtools`: aeternum,
  el-openglo (plus about 40 agent worktrees under `.claude/worktrees`, which are copies, not
  consumers), gabion, gcalculus, linux-sources (and its `.linux-sources-gate-wt` worktree),
  paperkit, resumes, rosettapkg, substrate, summit, amr-skills, life.
- Inside mtools: 34 dist `pyproject.toml` files name `mikemol/mtools` (sibling dependencies as
  git references); a split must rewrite each to the sibling's new repository or to the index.
- READ (W1229, 2026-10-14, from each consumer's `pyproject.toml` pin lines; `uv.lock` files were
  not read): every pin is `git+https://github.com/mikemol/mtools.git@<sha>#subdirectory=<dist>`.
  Shas in use, by repository (dists pinned):
  - `03749d56d557...`: life (pathsforward, hooks, transcriptstruct, gmailstruct); substrate
    (mdstruct, hooks, fence, transcriptstruct, corpus, witness, ratchet, ledger, pathsforward).
  - `f04f0a2f6b93...`: gcalculus (hooks, pathsforward); linux-sources (hooks, fence, pathsforward,
    pycodemod, mdstruct); el-openglo (mdstruct, hooks, pathsforward, pycodemod, atomicwrite,
    grade, bibparse, pytestspec, fence).
  - `c3ca6d249eff...`: summit (hooks, mdstruct, pathsforward, pathwalk, pycodemod, witness).
  - `2eeb11eba415...`: paperkit (atomicwrite, grade, hooks, pathsforward, pkgbuild, gatecheck,
    mutation, bibparse, mutantcell, memres, buildtel, importdag, rulerseq).
  - `7aa3b8fa2e87...`: gabion (pathsforward).
  - Named but with no pin line my pattern matched (prose, or a different form; unread): aeternum,
    rosettapkg, resumes, amr-skills.
- CONSEQUENCE: five different shas are pinned, and the most-pinned dists are pathsforward (eight
  repositories) and hooks (seven), so these two (and fence, mdstruct, pycodemod) are what a
  consumer breaks on first. A pin by sha keeps resolving while `mikemol/mtools` exists with
  those commits reachable, so the old repository must stay, with history intact, until the last
  consumer has re-pinned to the index release or the new repository.

## History rehearsal (W1225, atomicwrite, scratch only)

Done 2026-10-15 in the session scratchpad, pushing nothing: `git clone --no-local` of
`/home/mikemol/github/mtools`, then `git filter-repo --subdirectory-filter atomicwrite --force`.
Readings: the clone parsed 1,261 commits and the filtered history kept 9 commits (those that touched
`atomicwrite/`); the `.git` is 348 KB; the repo's HEAD is the last commit that touched the dist
(`W1207`, the LICENSE one). `mikemol-privacy-audit --history REPO .` over the filtered repo:
`{"deny": 0, "files": 33, "withheld": 0}`, so for this dist the history carries no finding.

What this does NOT show: other dists (the ones with home paths in tests or policy files, W1231,
W1232, would show findings in their history); tags (the monorepo has no per-dist tags, so there is
nothing to carry and the first release tags are new in each repo); commit messages, which keep their
`W<n>` waypoint trailers and so name cards of the monorepo's queue; and the cross-dist commits (a
commit touching several dists is rewritten once per filtered repo, with the other dists' paths
dropped, so its message describes work partly not in that repo).

## Gate and release workflow shape (W1226; options inside the ruled plan)

Facts read from the tree, 2026-10-15: today's gate is local (`hooks/bin/mikemol-commit`, bazel,
pre-commit hooks), not Actions; `.github/workflows/` holds one file, `publish.yml`
(dispatch-only); `ci/module-gate.yml` is the unwired draft of the per-module gate. So the
monorepo's Actions spend today is the publish workflow only, near zero (billing facts above).

Options for the release workflow after a split, each with its cost:

1. A copy of `publish.yml` in every one of the 34 repos. Cost: 34 files to keep in step; a change
   to the SHA-pinned actions or the opa fetch is 34 edits (a bot or `mikemol-repin`-style verb would
   be needed). Benefit: each repo's pending publisher names its own `publish.yml`, no indirection.
2. One reusable workflow in `mikemol-tools/workflows` that each repo's small `publish.yml` calls.
   Cost: the callers still exist (34 tiny files), and the registration interaction below is
   UNVERIFIED. Benefit: one place for the pinned actions and the preflight steps.
3. Keep publishing from one place (a `mikemol-tools/release` repo that checks out each dist repo at
   a tag). Cost: the pending publisher then names that one repository for all 34 projects, which
   defeats per-repo provenance, and the build is no longer from the dist's own repo.

READ 2026-10-15 (W1235), docs.pypi.org/trusted-publishers/troubleshooting/, as the fetch tool
rendered the page: "Reusable workflows cannot currently be used as the workflow in a Trusted
Publisher." and that this "is a practical limitation, and is being tracked in warehouse#11096."
The page does not say which file a call is matched against, so the consequence is the conservative
one: the job that holds `id-token: write` and runs the upload must live in the repository's OWN
`publish.yml`, so that file is what each pending publisher names. Option 2 is therefore safe only
for the steps before the upload (build, `release-check`, preflight), not for the publishing job;
option 1 (a copy per repo) is what registration allows today. Not verified by observation; the
TestPyPI dry run of one dist (W1152) would confirm it.

The gate side (one monorepo gate versus 34 per-repo gates) is already ruled: per-repo gates on the
reusable `module-gate.yml` and the self-hosted runner (W319), with the cross-package tests
atomized (W318). What remains open for the operator is the order and the go to push.

## What already works for it

A layout file (TOML, format in `mikemol.pkgbuild.repos`; none is tracked yet, and with none every
dist is `mikemol/mtools`) maps each dist to owner/repo; the
`publishers` and `environments` modes read it with `--repos FILE`, so the same commands work after
a split with no code change.
