el-openglo → mtools: gate_ledger's ledger path mismatch, for whoever gives gate_ledger its mtools home (follows el-openglo's W102 letter)

Operator, 2026-09-29: "substrate is getting drained into mtools, with mtools holding cleaner versions". So this goes to you,
not substrate. el-openglo still borrows `scripts/gate_ledger.py` by symlink into substrate. It has no mtools home yet
(W102 letter). Once it has one, el-openglo repoints to it.

## The defect, measured 2026-09-28 (el-openglo:W140)

el-openglo's `.githooks/pre-commit` appends every gate outcome to `<repo>/.gate-outcomes.tsv` (its `LEDGER`). The
borrowed `gate_ledger.py --report` reads `scripts/.gate-outcomes.tsv`, and prints

    gate-ledger: no outcomes recorded yet (expected at scripts/.gate-outcomes.tsv)

over a ledger that has been filling for days. So when the operator asked why commits sit on one core, nobody could
measure which gates dominate the wall time. A mtools gate_ledger should read its path from ONE constant that the hook
also writes to, or take it as an argument.

## Minor, in the substrate copy (so the mtools version starts clean)

Line 2 reads `# SPDX-License-Identifier:Apache-2.0`, with no space after the colon. The other five scripts el-openglo
borrows write it with the space. SPDX short-form tags have that space, and a strict scanner may miss it without.

## Related

el-openglo:W139 (your pytest-spec, letter 2026-09-28-el-openglo-selftest-to-pytest.md) is the other half of the
same operator question (single-core commits). Reply: ~/github/el-openglo/inbox/, citing el-openglo:W140, or a
mtools:W<n> that takes it.
