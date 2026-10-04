# W317 — splitting mtools into a GitHub org, one repo per distribution

The operator's direction (2026-10-01): "switch from a single repository to a GitHub org that has a
repo per module. That allows more freedom." This is the inventory and the order. Nothing touches
GitHub until the operator confirms: creating the org and pushing repos is public, and hard to undo.

## Measured: the packages are already independent

- **13 distributions**: audiostruct, corpus, fence, hooks, icsstruct, ledger, mdstruct,
  pathsforward, pycodemod, pytestspec, ratchet, transcriptstruct, witness.
- **0 cross-distribution imports** in src/ or tests/, read by `ast` over every `.py`. Positive
  control: the same reader saw 436 same-distribution `mikemol.*` imports, so the zero is not
  blindness. No pyproject declares another mtools distribution as a dependency.
- So the coupling is **entirely shared infrastructure**, not code. That makes the split mechanical,
  not a refactor.

## What is repo-wide today (each needs a new home)

| thing | today | after the split |
|---|---|---|
| Bazel module | root `MODULE.bazel` (31 `pip.parse` hubs), `.bazelrc`, `.bazelversion`, `BUILD.bazel`, `venv.bzl`, `patches/`, `rbe/` | each repo has its own `MODULE.bazel` with its own hubs. `venv.bzl` and the shared rules become a Bazel module in the tooling repo, pinned by `git_override` at a commit |
| check drivers | `ruff_check.sh`, `mypy_check.sh`/`mypy_runner.py`, `mutate_check.sh`/`mutate_runner.py`, `ratchet_check.sh`, `shellcheck_test.sh`, `pytest_main.py` | in the tooling module, referenced as labels, like today |
| git hooks | `.githooks/` pre-commit, commit-msg, post-commit (push) | a hook set in the tooling repo, adopted per repo, as the fleet already does through `mikemol-hooks` |
| cross-package gates | hooks' `test_bar_fires` (globs `*/pyproject.toml`), `test_venv_artifact`, `test_routing_table` | each repo runs them over itself, and a fleet census covers invariants across repos (nemik's job, or a summit check) |
| house docs | `SKELETON.md`, `INSTALL.md`, `README.md`, `LICENSE` | SKELETON becomes a **template repo** (new modules start from it). Each repo carries its own INSTALL section and its own LICENSE |
| workstream | `.claude/` queue, `inbox/`, `findings/`, the paths-forward loop | stays with the mtools repo (below) |
| the harness | this session's `.claude/settings.json` runs `hooks/bin/` launchers | repointed at the installed `mikemol-hooks`. ⚑ This is the session's own guardrail, so it moves LAST, with a measured fail-closed check |

## Operator rulings, 2026-10-01 (second message)

> "one version for all dependencies" was a convenient side effect of mtools as a monorepo, and
> helped ensure individual agents kept up-to-date with capabilities added on behalf of other agents.
> The individual repos can get their own build gates. Also, conveniently, at least some of GitHub
> Actions becomes ~free to an org that's open source. So we can leverage that.
> Tests that span packages should be atomized.

What follows:

- **D4 withdrawn, and its purpose kept.** The one-version rule was doing real work: it moved every
  agent onto every new capability. The split must replace that, not lose it. Its successor has two
  parts:
  - **Automated pin bumps.** A bot (Renovate handles git-sha pins; Dependabot's uv support is
    worth checking) opens a PR in each consuming repo when a module it pins releases. The
    consumer's own gates decide whether it merges.
  - **A fleet staleness census.** For each consumer and module, how far its pin is behind the
    module's head: nemik's job, or a summit check. A stale pin becomes a visible row, not a silent
    drift. This is the "kept up to date" property, made observable instead of forced.
- **Per-repo gates on GitHub Actions.** Public repos get Actions at no cost. Each module repo's
  workflow runs its own bazel suite (ruff, mypy, mutants, tests, warrants), from a reusable
  workflow in the tooling repo, so the gate is defined once and pinned. ⚑ The buildbuddy remote
  cache on luthen is not reachable from Actions runners: either run without it (each suite is
  small), or expose a read-only cache. To be measured on the pilot. The local pre-commit gates
  stay as they are.
- **Cross-package tests are atomized.** The three hooks tests that sweep every package
  (`test_bar_fires` over `*/pyproject.toml`, `test_venv_artifact`, `test_routing_table`) become
  per-repo checks, each run by that repo over itself. Any remaining fleet-wide invariant is a
  census row (above), never a test that spans repos.
- **Visibility is not a new exposure.** github.com/mikemol/mtools is already PUBLIC (gh repo view,
  2026-10-01), so the split repos publish nothing new. Their histories are subsets of a public one.

## Operator, 2026-10-01 (third message): two mechanisms for keeping agents current

> We can do that with a "meta" package. Or through transitive dependencies all requiring >= as dev
> deps every time something implements something on their behalf.

They do different jobs, and the plan takes both:

- **Floors, `>=` (correctness).** When a module ships something a consumer asked for, the
  consumer's dependency gains a floor at the version that has it, written in the same change that
  adopts it. The floor says "this repo NEEDS at least this", tied to the ask. It can never drift
  below what was built for it, and a resolver refuses an older module outright. This is the
  precise successor to the one-version rule.
- **A meta package (freshness).** `mikemol-mtools` (name to taste) has no code and one dependency
  per module, each at its latest release, and is republished when any module releases. A consumer
  that wants "everything current" pins only the meta package: one pin to bump, as today. Heavy or
  platform-bound modules (audiostruct's GPU set, any Qt one) sit behind extras, so the meta package
  never imposes them.
- ⚑ **Both need real versions.** `>=` cannot compare git shas, and today every module is 0.1.0,
  pinned by sha. So each module gets semantic versions and release tags, cut by its Actions
  workflow, and published where a resolver can read versions. **D5**: PyPI (the repos are public
  anyway), or GitHub Releases as a `--find-links` index.
- The pin-bump bot and the staleness census stay. They are what makes a stale floor or meta pin
  visible. Renovate reads version ranges natively once versions exist.

## Operator, 2026-10-01 (fourth message): our own runner, and gitops to PyPI

> we can ask luthen-observability to maintain a runner for us, and then our tests run under our
> runner, orchestrated by GH. [...] push to stage, merge to main, stage goes to testing pypy, main
> goes to public pypy, going to public is gated on tests passing.

**D5 is answered: PyPI, with TestPyPI as staging.** The pipeline per module repo:

| event | runs | publishes |
|---|---|---|
| push to `stage` | the module's full gate on our runner | a `.devN` build to **TestPyPI** (a version can never be re-uploaded there, so stage builds take dev versions) |
| merge to `main` | the same gate | a release to **PyPI**, only when the gate passed (`needs:` on the test job) |

- **Trusted Publishing (OIDC)**: PyPI and TestPyPI trust each repo's workflow directly, so no
  upload token is stored anywhere, on GitHub or on the runner.
- Versions come from tags (setuptools-scm or similar), which is what makes the `>=` floors and
  the meta package work.

**The runner: luthen-observability maintains it, and GitHub orchestrates it.** It reaches the
buildbuddy cache, so the unknown above goes away.

⚑⚑ **A SELF-HOSTED RUNNER ON A PUBLIC REPO RUNS STRANGERS' CODE unless it is fenced.** Anyone can
open a pull request from a fork, and a workflow that runs on that PR executes the fork's code on
our runner, inside luthen's cluster. GitHub's own guidance is not to use self-hosted runners with
public repos for exactly this reason. The fences, all required:

1. **Ephemeral runners**: one job per pod, then the pod is destroyed (actions-runner-controller on
   luthen's k8s). Nothing persists from one job to the next.
2. **Fork PRs never reach our runner.** Gate on the event and the repo: our runner runs `push`
   (stage, main) and same-repo PRs. A fork PR either waits for an approval ("require approval
   for all outside collaborators") or runs on a GitHub-hosted runner.
3. **The runner holds no secrets** (OIDC handles publishing), and its pod has no cluster
   credentials and only the network egress it needs.
4. **An org runner group** limited to the module repos.

This is luthen-observability's design to make. The ask is mtools:W319, minted there as
luthen-observability:W257. Their additions (2026-10-01):

5. **Cache poisoning: the fence they worry about most.** A runner that writes to the shared
   BuildBuddy CAS can poison every build that reads it. PR jobs get **read-only** cache access.
   Only push-to-stage and push-to-main jobs write, into their **own `remote_instance_name`**,
   never the instance luthen and other tenants build from.
- A separate namespace and pool (not the BuildBuddy executors), restricted Pod Security Admission,
  and a default-deny NetworkPolicy with an egress allowlist of GitHub, PyPI/TestPyPI and the cache
  only.
- Registration uses a GitHub App. Its private key is held machine-side in OpenBao, never in a
  file or a tree, and never handled by an agent.
- actions-runner-controller is a privileged cluster apply, so the operator reviews a written
  design first.
- Sizing comes from a measured job, not a guess: mtools:W320 profiles one module gate, cold and
  warm. Cold fetches go through BuildBuddy's remote downloader cache, if bazel accepts
  `--experimental_remote_downloader`.

**D1, the org name.** The operator said `mikemol_tools`, but GitHub org names allow only letters,
digits and hyphens. `mikemol-tools` and `mikemoltools` were both unclaimed on 2026-10-01
(`gh api users/<name>`: 404). Awaiting the operator's pick.

## Operator, 2026-10-01: D1, D2, D3 answered

- **D1:** the org is **`mikemol-tools`**.
- **D2:** each repo keeps its git history.
- **D3:** mtools stays as the **workstream repo** (queue, inbox, these ticks). The shared machinery
  becomes module repos, with the operator's condition: **"I'll insist on atomization and
  composition."**

So there is no monolithic "tooling" or "gates" repo. The shared machinery splits along
responsibilities, and each module repo composes only the pieces it uses. A draft cut, to be
measured against the real call sites (mtools:W321) before it is final:

| atomic module | today | composed by |
|---|---|---|
| bazel python rules | `venv.bzl`, the py_test-per-module pattern, `pytest_main.py` | every Python module repo |
| ruff check | `ruff_check.sh` | every module repo |
| mypy check | `mypy_check.sh`, `mypy_runner.py` | every module repo |
| mutation check | `mutate_check.sh`, `mutate_runner.py` | module repos that gate mutants |
| ratchet | already `mikemol-ratchet`, plus `ratchet_check.sh` | module repos with a preview baseline |
| shellcheck test | `shellcheck_test.sh` | repos with shell |
| git hook set | `.githooks/` pre-commit, commit-msg, post-commit | every repo; mostly already `mikemol-hooks` |
| reusable Actions workflows | new | every module repo; one workflow per check, composed by the repo's own workflow |
| module template | `SKELETON.md` → a GitHub template repo | new modules |

**Measured against every call site (W321, 2026-10-01, `scratchpad/callsites.py`: every tracked text
file that names each of the 24 root scripts. Positive control: venv.bzl is named by 13 of 13
distribution BUILDs).** The draft is confirmed for the atoms and corrected for the rest:

| root file | named by | verdict |
|---|---|---|
| `venv.bzl`, `pytest_main.py` | all 13 distributions | **atom: bazel python rules** (W323) |
| `ruff_check.sh` | all 13 | **atom: ruff check** (W324) |
| `mypy_check.sh`, `mypy_runner.py` | all 13 | **atom: mypy check** (W325) |
| `mutate_check.sh`, `mutate_runner.py` | all 13 | **atom: mutation check** (W326) |
| `ratchet_check.sh` | all 13 | **atom: ratchet check**, beside `mikemol-ratchet` (W327) |
| `shellcheck_test.sh` | hooks and root BUILD | stays in mtools for now: only the repo gate uses it. A shellcheck atom waits for a module with shell |
| `preflight.sh`, `blockers.sh`, `figure_freshness.sh`, `rule_freshness.sh`, `rule_citations.sh`, `message_counts.sh`, `orphan_check.sh`, `roster_drift.sh`, `refusal_record.sh`, `domain_witness.sh`, `collect_check.sh`, `count_test_functions.py`, `git_env.sh`, `setup.sh`, `bep_probe.py` | the root gate (`.githooks/`, `preflight.sh`, root BUILD) and hooks' tests of that gate | **stay in mtools**: they govern the workstream repo itself, and their hooks tests (most of W318's 40 bar_fires sweepers) move with them |

A check is an atom. A module repo's gate is the composition it declares. Each atom is versioned
and pinned with `>=` floors like any other module. The meta package covers the modules, not the
atoms.

## What mtools becomes

It is kept, not archived: the **workstream repo** (operator decision D3). It holds this queue, the
inbox, the ticks, and its **own gate**: the root scripts that govern the workstream repo itself
(`preflight.sh`, the citation, freshness, orphan and roster gates, `refusal_record.sh`,
`domain_witness.sh`, `shellcheck_test.sh` until a module needs a shellcheck atom) and the hooks tests
of that gate (W339 below). It is **not** a tooling monolith that module repos pin. The shared
machinery leaves as separate atomic modules, each versioned and composed only where used: the bazel
python rules (`rules_py`, W323), and the ruff, mypy, mutation and ratchet checks (`check_ruff`,
`check_mypy`, `check_mutants`, `check_ratchet`, W324-W327), plus the git hook set and the reusable
Actions workflows as their own modules. A module repo's gate is the composition of atoms it declares;
mtools' gate is one such composition, over itself. (Rewritten 2026-10-03, W346: the earlier text
had mtools holding the Bazel tooling module and check drivers for every repo to pin, which D3's
"I'll insist on atomization and composition" and the W321 call-site measurements both rule out.)


### Tests that stay with mtools (W339)

The census (W318, re-run 2026-10-01) found 61 of hooks' 499 test functions reaching outside
`hooks/`. These stay in mtools' own gate, because their subject is mtools itself, not a package:

- **`test_routing_table.py`, 11 tests.** They read the repo's routing table, which decides which
  tool owns which file type. That table is mtools' harness configuration.
- **`test_no_verify.py`, 2 tests.** They read `.claude/settings.json` and the post-commit hook,
  both of which are mtools' own.
- **`test_bar_fires.py`, 31 of its 40 root-reaching tests.** They test the commit gate itself:
  pre-commit and preflight, the witness and its probes, the citation, orphan and freshness gates,
  the census poll, the git-environment scrub, the rule that no hand-written list of packages
  survives, and the rule that the gate never runs a second copy of a check the graph already runs.

What moves instead:

- `test_venv_artifact.py`'s 8 tests: a shared venv check in `@mikemol_rules_py` that each package
  runs over its own `.venv` (W341, W342, W343).
- `test_bar_fires.py`'s other 9: suite hygiene, 4 tests, as a per-package check (W344), and
  ruff/ratchet configuration, 5 tests, into `@mikemol_check_ruff` and `@mikemol_check_ratchet`
  (W345).

61 = 11 + 2 + 31 + 8 + 9.

## Order: smallest coupling first, the harness last

0. **Atomize the cross-package tests** inside mtools first: each of the three sweeping hooks tests
   becomes a check a single package runs over itself. This needs no repo move and no org, and it
   is right whether or not the split happens.
1. **Extract the tooling module** inside mtools first (rules, drivers, hooks as a self-contained
   Bazel module), with no repo move yet. Every distribution's BUILD then references it the way a
   split repo will. This is the step that makes the rest mechanical.
1b. **The reusable Actions workflow and the pin-bump bot** in the tooling repo, so the pilot is
   born gated and watched.
2. **Pilot one leaf**: `icsstruct`. It has few consumers (life, nemik soon), a stdlib core and its
   own small hub. `git filter-repo --subdirectory-filter icsstruct` keeps its history (D2). Its
   own MODULE.bazel pins the tooling module. Measure it: its bazel suite green in the new repo,
   `mikemol-ics` installable from the new URL, and consumers repinned.
3. **The other leaves**, in order of consumer count, fewest first: transcriptstruct, audiostruct,
   corpus, witness, ledger, ratchet, mdstruct, pytestspec, fence, pycodemod.
4. **pathsforward**: the most consumers (the whole fleet's queues). Coordinate the repin through
   nemik, whose AdoptionShape check reads INSTALL.md.
5. **hooks last**: it is this session's harness, and splitting it changes what guards the commits
   doing the splitting.

## Operator decisions

- **D1** the org's name.
- **D2** keep each module's history (default yes, by `git filter-repo`).
- **D3** mtools stays as the tooling and workstream repo (recommended), or is archived.
- **D5** where versioned releases are published: PyPI, or GitHub Releases as a find-links index.
- ~~D4 drop the one-version pin rule now~~: **withdrawn** by the ruling above. The rule's purpose
  carries over as pin-bump PRs and a staleness census.

## Waypoints to mint once confirmed

One per step above: 0 (atomize; can start NOW, since it needs no decision), 1, 1b, 2 (pilot), one
per leaf in step 3, 4 and 5. Plus the staleness census (nemik or summit; ask them). Each is one landable unit
with its own check. Step 1 is the only real engineering, and the rest repeat the pilot.
