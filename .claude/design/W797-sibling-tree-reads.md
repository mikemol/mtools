# W797: gates and checks that read a sibling repo's live working tree

Audit of 2026-10-11. Method: `grep -rE` over `~/github` for `Path.home() / "github"`,
`expanduser("~/github/...")` and `github/<repo>` in `*.py *.sh *.bzl *.bazel *.toml pre-commit
Makefile *.mk`, excluding `.venv .git bazel-* node_modules __pycache__ .claude worktrees processed
archive inbox`. **Evidence arm:** the matching lines only (file:line); I did not open each file, so the
role of a script (gate or tool) below is read from its name and location, and is a claim to confirm
by its owner. **Not covered:** shell scripts that build the path from a variable, `.rego`/`.md`
sources, repos I cannot read (`luthen-observability/.kube` refused), and reads through `$HOME`
without `github`. UNAVAILABLE is not absent.

## A. Already pinned (no card)

- Every repo's `MODULE.bazel` that names `/home/mikemol/github/mtools` or `/home/mikemol/github/paperkit`
  does so as a `git_override` remote with a recorded commit (aeternum, amr-skills, el-openglo,
  gcalculus, resumes, rosettapkg, substrate). The remote is a local path; the content is the commit.
- resumes: its pre-commit says the paperkit engine "is now a recorded commit".
- linux-sources `checks/bibprobe.py`: "THE CHECKOUT, AND ONLY THE CHECKOUT"; paperkit is pinned in its
  pyproject (W33, 4c4e231).

## B. Candidates: a gate or check that certifies from a sibling's live tree

| reader | reads | note |
|---|---|---|
| el-openglo `scripts/worklist_gate.py:81` | `~/github/paperkit` (the engine) | engine located by live checkout |
| el-openglo `scripts/check_discriminates.py:70` | `~/github/paperkit/paperkit/mutate.py` | live mutate engine |
| el-openglo `scripts/check_wall_limits.py:323` | `~/github/substrate` | one of a candidate list |
| el-openglo `gcalc_api.py:29` | `~/github/gcalculus` | live API |
| gcalculus `grade.sh:44` | `/home/mikemol/github/paperkit/paperkit` | `check.sh:297` says it uses named inputs; this does not |
| rosettapkg `lattice/cite-check.py:111` | `~/github/linux-sources` | the known case (rosettapkg:W121) |
| rosettapkg `lattice/ledger-check.py:137,566,626,899,906` | linux-sources, then every repo | a walk of the whole host |
| linux-sources `linux_sources/paperkit_locate.py:28` | `~/github/paperkit/paperkit` | a locator; bibprobe is the pinned half |
| linux-sources `ls_gate/ledger_evidence.py:60` | `~/github/mtools/mdstruct/.venv/bin/mdstruct` | a built tool in mtools' tree |
| linux-sources `ls_gate/blocker_predicates.py:137` | `~/github/summit/registries/capabilities` | a registry read by a predicate |
| summit `ledger/check.py:73`, `scripts/engine.py:31` | `~/github/paperkit` | default repo |
| resumes `groundings/checks/grounding.py:102` | `$PAPERKIT_ENGINE` else `~/github/paperkit/paperkit` | env override, live default |
| cassian-obs `pm/checks/ledger-check.py:25` | `~/github/paperkit` | default repo |
| amr-skills `amr_agree.py:37`, `collapse_probe.py:31`, `amr_jea.py:33` | `~/github/substrate` | `sys.path` insert of a live tree |
| aeternum `scripts/lore.py:29` | `~/github/amr-skills` | |
| mikemol.github.io `scripts/build_posts.py:92` | `$PAPERKIT_ENGINE` else paperkit | |
| mtools `.githooks/pre-commit`, `blockers.sh`, `rules_py/*` | named hits, not yet read | mtools' own, to check first |

## C. Fleet readers by design (not pin candidates)

They exist to read every repo's working tree: luthen-observability `checks/*` (nemik_check,
fleet_par, loop_liveness, ledger_timestamps, alert_notify, nemik_export, nemik_publish, host_live),
nemik (`check.py`, `overlaps.py`, `vtodo.py`), gcalculus `scripts/inbox_fold.py`, linux-sources
`checks/hookcensus.py` and `sent_census.py`, summit `scripts/*`, gabion `paths_forward_state.py` (its
own tree). A live read is their job; what they owe is naming the root they read (a `--root`).

## What a fix is, mechanically

A reader in B has two honest forms: (1) read a recorded commit (a `git_override`, a vendored wheel, or
`git -C <repo> show <sha>:<path>`), or (2) read the live tree and REFUSE to certify when that tree is
dirty or not at the recorded sha. Form 2 is one check shared by every reader: given a repo path and a
sha, exit 0 only when HEAD is the sha and the tree is clean, and say which. That is the tool
(mtools:W1018). The adoption in each repo is that repo's own card, asked by letter (mtools:W1019).
