# mikemol-pytestspec

A pytest plugin that collects Rego specs and runs each one as a test item.

A spec is written against the **origin** tool's output and evaluated by a pinned `opa`. That
makes it a checker that neither the origin nor its port wrote. Each case maps to a verdict:

| spec verdict | pytest outcome |
|---|---|
| `admitted` (no deny, no withheld) | pass |
| `deny` non-empty | fail, with the deny messages |
| `withheld` non-empty | fail, marked UNMEASURED; it is never a skip |
| `opa` absent or not the pinned version | fail; it is never a skip |

Status (W194, split into W198/W199/W200):

- W198, this shell: it declares which files are specs (`plugin.claims`). A `.rego` file counts;
  opa's own `_test.rego` does not.
- W199: collection and the verdict mapping. Cases live in `<spec>.cases.json` beside the spec.
- W200: the default evaluator is `opa eval` over the spec's `package`, with opa pinned to
  1.20.2 (`opa.PINNED`). A test can replace it through `config.stash[plugin.EVALUATOR]`.

A spec must define a `deny` rule. A package document with no `deny` is withheld, never
admitted: a spec with no rules would otherwise pass every case, which is what happened before
W200 fixed it.

## Dispositions (W201)

A case may declare a `disposition`, with a `reason` it must give:

| disposition | outcome |
|---|---|
| `do-not-port` | deselected; pytest's `deselected` count reports it |
| `unmeasured` | xfail(strict): never a pass, and a pass FAILS until the declaration is removed |
| `port-fix` | runs normally; `pairs_with` must name the case that pins the origin's row |

A withheld verdict with no declaration is still a plain failure. An unknown disposition, a
missing reason, or an unpaired port-fix is a collection error.

## Expected outcomes (W372, W381)

A refusing fixture declares the rules that must deny it, and a could-not-measure fixture the
rules that must withhold it:

    {"case": "s0-refuses", "expect": {"deny": ["S0"]}, ...}
    {"case": "null-lint", "expect": {"withheld": ["W"]}, ...}

Each message's rule id is the text before its first `:`, so `S0: refused` has the id `S0`. Ids
match exactly, so `S1` never matches `S10`. The case passes only when the denying ids equal
`expect.deny` AND the withholding ids equal `expect.withheld`. **An omitted key means that set
must be empty**, so a deny fails a case expecting only a withhold, and a withhold fails a case
expecting only a deny (a rule that did not run did not refuse). A mismatch fails as `DENY
MISMATCH` and/or `WITHHELD MISMATCH`, each naming its missing and unexpected ids. Without
`expect`, a case is admitted-only, as before. A bare `"expect": "denied"`, an `expect` naming no
id, an unknown key or a non-string id is a collection error. Asked for by el-openglo (W139 for
denies, W211 for withholds), whose rule tests carry refusing, admitting and could-not-measure
fixtures.

## Shared libraries (W380)

A spec that imports a helper package (`import data.el.truth`) compiles only if the helper is
loaded too. Declare the helper paths in the pytest config:

    [pytest]
    pytestspec_data = policy/lib

Each path is passed to `opa eval` as an extra `--data`, beside the spec. Nothing is loaded
implicitly: a sibling directory that is not declared is never guessed. A declared path that does
not exist is a collection error. A `.rego` file under a declared path is a library, not a spec,
so it is not collected. A spec whose import nothing loads fails as UNMEASURED, and the failure
names opa's compile error.

## Implementation adapters (W202)

A conftest or plugin offers implementations through the `pytest_spec_implementations` hook,
as `{name: adapter}`, where an adapter is `adapter(fixture, operands) -> result`. With
`--impl NAME`, each case's `result` comes from running that implementation on the case's
`fixture` and `operands`, so one spec judges the origin (`--impl reference`) and the port
(`--impl subject`) on the same data. An unknown name, a name offered twice, or a case with no
`fixture` fails as UNMEASURED. Without `--impl`, a case is evaluated as written.

## The differential line (W203)

Every run ends with one line per spec, every column always printed:

    pytestspec: spec.rego impl=subject admitted=2 denied=1 refused=1 withheld-expected=1 unmeasured=1 do-not-port=1 port-fix=1 declared-skipped=0 cached=0

`impl` is the `--impl` in force, or `as-written`. A declared-unmeasured case (xfail) counts as
unmeasured; do-not-port and port-fix count declarations, whatever their outcome. Every passing
case lands in exactly one column: `admitted` (no `expect`), `refused` (an `expect` naming a
deny, met), or `withheld-expected` (an `expect` naming only withholds, met). A `DENY MISMATCH`
counts as denied, and a `WITHHELD MISMATCH` alone as unmeasured.

## Parallel runs (W316)

Each case is an ordinary pytest item, so pytest-xdist (`-n N`) runs them in parallel with the
same outcomes as a serial run. The differential line is printed by the controller, from the
tallies each worker hands over when it finishes. Declarations are taken once, because every
worker collects every case. Outcomes are summed, because each case runs on exactly one worker.
xdist does not cap memory: put the cap around the whole run (for example
`systemd-run --user -p MemoryMax=8G -- pytest -n N`).
