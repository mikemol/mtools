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
- W199: collection and the verdict mapping, over an injected evaluator.
- W200: the pinned `opa eval` evaluator.
