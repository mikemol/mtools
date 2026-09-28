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
