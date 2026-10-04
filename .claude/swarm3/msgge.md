W495 / msgGE.txt (drafter msgge)

DELIVERED: yes. /home/mikemol/github/substrate/inbox/2026-10-01-mtools-pycodemod-guarded-contract.md
carries msgGE.txt's body word for word. The delivered copy adds a subject line naming mtools:W204
and a closing "Reply by citing mtools:W204" line. There is no inbox/archive/ dir in substrate.
`summit ask --for substrate` shows no matching ask (12 asks, none about --guarded). That is
expected, because this went as a letter, not a summit ask.

REPLY: none found. mtools/inbox/ has no substrate letter citing W204 or --guarded dated after 2026-10-01.

CURRENT? The contract claim is still current. The pycodemod log since 2026-10-01 has only
differential/capture/opa commits, and no commit changes the guarded negation. The cited
evidence paths have gone stale, though:
- .claude/design/W196-spec/ (guarded.rego, guarded_test.rego) and .claude/design/W210-elif.py
  still exist, but they are untracked. Substrate cannot read them, and they break the
  no-load-bearing-code-in-.claude rule.
- pycodemod/differential/ tracks guarded.cases.json but has no guarded.rego or
  guarded_test.rego. The other specs migrated there (a838c40, 564dfc2, bebafd7); the guarded
  spec did not.

PROPOSED ACTION:
- msgGE.txt is retired as delivered, with evidence: the substrate inbox path above. It is
  scratch and can be deleted by the queue owner. I deleted nothing.
- Mint a waypoint to move guarded.rego and guarded_test.rego into pycodemod/differential/,
  under the opa bazel test. A short follow-up note to substrate can then repoint the
  evidence paths. Do that only after the move, and send nothing now.
- Keep W204 open, waiting on substrate's answer.
