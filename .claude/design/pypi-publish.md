# mtools published on PyPI (W1143)

Goal node W1143. Every open mtools card that must finish first enables it, so each leaf has the
goal downstream. The burn-down is whatever `nemik-rank mtools --goals` shows ready on the frontier.

## Readiness cards (enable W1143)

| requirement | card |
|---|---|
| reuse-readiness census, boundary policy in Rego | W1047 (existing) |
| privacy and secret audit | W1144 |
| a license per dist | W1145 |
| installable guide that works off this host | W1146 (extends W1104, existing) |
| tests that run off this host | W1147 |
| no baked-in host specifics | W1148 |
| PyPI metadata, names free or owned | W1149 |
| versions tied to waypoints | W803 (existing) |
| wheel route's own checklist | W1136 (existing) |
| the publish waldo | W1150 |

## The waldo, W1150

Nothing is published without the operator. Preflights are live facts, each its own card:

- W1151 clean build of every dist from the pinned sha, `twine check` on each artifact.
- W1152 a TestPyPI upload first, and an install from it in a clean venv.
- W1153 operator act: register trusted publishers (no stored token; a key is never typed into a card).
- W1144 and W1148 (privacy audit and host specifics) also enable W1150: no upload with either red.

The final upload is the operator's act. The names are decided (W1195, 2026-10-14) and the workflow
exists: `.github/workflows/publish.yml`, trigger `workflow_dispatch` only, input `index` =
`testpypi` or `pypi`, environments `testpypi` and `pypi`, repository `mikemol/mtools`. Every dist's
project name is `mikemol-<dir>` (`mikemol-wheel names .` prints them; all 34 read free on both
indexes on 2026-10-14). The workflow builds and checks every dist at the dispatched commit
(`mikemol-wheel release-check`: metadata, README render, shipped-file privacy judge) and uploads
exactly those artifacts through trusted publishing; no token exists anywhere.

## The operator's steps (W1153), in order

1. **GitHub, once:** repository Settings, Environments, New environment `testpypi` (no rules) and
   `pypi` (Required reviewers: yourself, so the real upload waits for your approval).
2. **TestPyPI, once per project (34):** test.pypi.org, Account, Publishing, "Add a new pending
   publisher". Fields: PyPI Project Name `mikemol-<dir>`; Owner `mikemol`; Repository name `mtools`;
   Workflow name `publish.yml`; Environment name `testpypi`.
3. **PyPI, once per project (34):** pypi.org, same page and fields, Environment name `pypi`.
   A pending publisher reserves nothing until the first upload, so it can be undone by deleting it.
4. **Dispatch TestPyPI:** repository Actions, "publish", Run workflow, index `testpypi`, version
   `0.0.N` where N is the number of a `publish` waypoint minted for this release (mtools:W803: the
   build's version is the card's number, strictly higher than anything minted before, so a version
   is never reused; the dists carry a placeholder `0.1.0` in git and the workflow stamps the
   release version into its build only). Expected: the build job green (34 rows ok, plus the
   INSTALL.md row) and the publish job uploading 68 files.
5. **Install check (W1152):** in a clean venv,
   `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ mikemol-hooks`
   and run `mikemol-commit --help`. Done when it installs and runs.
6. **Dispatch PyPI:** same, index `pypi`, with a version from a new publish card (the ruling mints
   a fresh card for each publish, and a retry mints a higher one; whether the TestPyPI number may
   be reused for the real upload is not ruled, so use a new one), then approve the `pypi`
   environment. Done when
   `pip index versions mikemol-hooks` lists it.

Undo: PyPI never deletes a release's filename for reuse; a bad release is yanked on the project
page, and the next version is a new upload. Delete a pending publisher on its page to withdraw trust.

The 34 project names: atomicwrite audiostruct bibparse buildtel corpus debtplan fence frontier
gatecheck gmailstruct grade gradekit hooks htmlstruct icsstruct importdag katas ledger mdstruct
memres mutantcell mutation pathsforward pathwalk pkgbuild procrun pycodemod pytestspec ratchet
rulerseq transcriptstruct treeio waldo witness (each prefixed `mikemol-`).

## Which open cards were NOT wired to the goal, and why

- Blocked cards: each waits behind a card that is wired, so it precedes the goal transitively.
- W317 chain (split plan), W592, W879, W796: operator-held; the split is not a PyPI precondition.
- W622 and W833: held on the operator and on paperkit:W295.
- W1007, W1008, W1030: host operations rows (luthen terraform, fence rail metrics), not publish blockers.
- W1151 to W1153: already descendants of the goal through W1150.

New cards: the exclusion is a judgement; move any card in or out with
`--update SYMBOL --add-enables W1143` or `--enables`.
