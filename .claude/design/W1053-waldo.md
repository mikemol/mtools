# W1053: the waldo mode (design note; no code yet)

Asked by luthen-observability:W889 (2026-10-12). A *waldo* is the operator's word (cassian-observability
session d90455f2): a narrow tool that holds ONE privilege and does only a declared action on behalf of
others. The permission classifier fires on the SHAPE of a command, not on a policy-checked plan, so the
privileged act has to be a named verb whose contract is declared in a file, not decided at a prompt.

## Sources read

1. `luthen-observability/checks/apply_set.py` + `checks/apply_sets/{main,host}.json` (W880/W882).
2. `amr-skills/peer_token.py` (W325/W340).
3. cassian-observability's six recipe files: NOT READ. `~/github/cassian-observability` does not exist on
   this host; luthen-observability-d9 named them as the idiom's home. Ask luthen where they live before the
   contract schema is frozen (open item, W1053-D below).

## What the two instances share (the extractable part)

| piece | apply_set | peer_token |
|---|---|---|
| a declared contract in a tracked file | `apply_sets/<name>.json` | the docstring + constants (not yet a file) |
| an identity must be chosen, never defaulted | the harness runs it as the operator | `--as-current-user` or `AMR_MINT_KUBECONFIG`, else REFUSE |
| the privileged act is one named verb | `--set <name>` | `mint` / `renew` |
| output that is safe to print | one JSON verdict line | fingerprint + expiry only |
| refusal applies nothing and says why | `-`/`+` diff + planned rows, exit 1 | "no identity chosen", exit via exception |
| the artifact checked is the artifact applied | the SAME planfile | the token that was minted is the one stored |
| after-the-act witnesses | event-bound `after` list | expiry read back from the token itself |
| custody | n/a | 0600 file in a 0700 dir, atomic rename, never printed |

## The shared contract (what a third waldo configures instead of rewriting)

1. **Declared allowed SUPERSET + required rows.** A converged row is simply absent from a plan, so an exact
   match refuses the first real run (measured 2026-10-12). Every planned row must be allowed; only
   `required` rows must be present.
2. **Refuse with a diff, apply nothing.** `-` required but absent, `+` planned but not allowed, plus the
   planned rows; exit 1.
3. **Apply the SAME artifact that was compared.** Plan fresh inside the command (under the contract's
   `plan_env`), compare, then apply that plan object; never a stale one.
4. **Witnesses that cannot pass on defaults or a retry.** Kinds: exit code, `json_empty` (keys must be
   PRESENT and empty), `must_contain`, `must_match`. Two mechanical rules the instances learned the hard way:
   a finished systemd oneshot unloads so `show` reads defaults (the witness must be the journal), and a
   witness that settles seconds after the act is a flake (keep it out of `after`; event-bound only, e.g.
   `rollout status` blocks until done). **Witness lint** (new, mechanical): at load time a witness is run
   against an EMPTY reading and a DEFAULTS reading; one that passes either is refused as a contract error.
5. **Fingerprint-only output; no secret ever in output.** A `Secret` value type whose `repr`/`str` is its
   fingerprint, stored 0600 in a 0700 directory by atomic rename; the only printable facts are the
   fingerprint (first 12 hex of sha256) and an expiry.
6. **One JSON verdict line, fixed state vocabulary:** `matches` (dry), `refused`, `applied`, `converged`,
   `apply-failed`, `*-witness-failed`, `cannot-run`; exit 0 matched/applied/converged, 1 refused or a step
   failed, 2 cannot run.
7. **Identity is an explicit choice.** A waldo refuses to run until the caller names which identity acts
   (a named machine identity, or an explicit `--as-current-user`); it never quietly becomes the operator.

## Shape of the code (a new stdlib-only dist, `mikemol-waldo`, module `mikemol.waldo`)

- `contract.py`: parse and validate a contract (allowed, required, plan_env, after, identity rule) from
  JSON; witness lint; pure.
- `compare.py`: `Change = (address, sorted actions)`, `compare(allowed, required, planned) -> Diff`,
  `render(diff)`; pure. Lifted from apply_set unchanged in behaviour.
- `witness.py`: run the four kinds over an injected runner; verdict per witness; pure but for the seam.
- `custody.py`: `Secret`, fingerprint, atomic 0600 write, identity-explicit refusal.
- `pipeline.py`: `execute(contract, seams)` plan -> compare -> apply the same artifact -> witness ->
  verdict; seams for run and summarize so each waldo supplies only its own plan and apply steps.
- `cli.py`: `mikemol-waldo --contract FILE [--dry]` plus a library entry point a repo's own named verb calls.

luthen ports `apply_set` onto it (its plan/summarize/apply are the two seams); amr-skills ports
`peer_token` onto `custody` + a contract with no plan step.

## What cassian's recipes add (read 2026-10-12 from the extract luthen made at
`~/.cache/cassian-recipes/cassian-observability/`: `docs/plans/plan-vault-apply-recipe-design.md`
through §6, `k3s/checks/recipe.py`; the `.sh` recipes themselves are not read yet)

The vault-apply design is a *sequence* of waldo-shaped phases (P-1..P10), each with a STAR-S gate that
REFUSES before and a STAR-R witness after. Five ideas the two built instances lack, all of which belong in
the shared mode:

1. **A `before` list (STAR-S), not only `after`.** Preconditions are MEASURED, never assumed, and refuse
   the whole run: tree clean, baseline resources present, no job in flight, fixes landed in HEAD. apply_set
   has only `after`. The contract gains `before` witnesses of the same four kinds.
2. **The witness must distinguish success from a byte-identical failure.** "A Job can complete green while
   the renew curl silently failed"; "SecretSynced=True can be a cached verdict"; "success state can be
   byte-identical to failure state". Two new witness kinds make this declarative: `advances` (a reading
   must differ from the pre-act reading, e.g. a resourceVersion or refreshTime) and `fresh_since` (a
   timestamp read from the target must be at or after the run's start, not a Job exit code). The lint of
   point 4 above generalises: a witness must fail on the empty, default AND pre-act readings.
3. **Verdicts that prove nothing say so.** recipe.py separates FAILED from SKIP ("proves nothing"), and a
   seamed-off step returns 0 with a verdict that says it proved nothing. The state vocabulary gains
   `skipped`; a skipped waldo is never reported as converged and never satisfies a downstream `required`.
4. **Halts are first-class.** `co-sign` (a human must run or approve a named step; the waldo detects
   and halts, e.g. a sudo import) and `point-of-no-return` (an explicit confirmation token, a typed phrase
   and not y/n, and every precondition RE-ASSERTED at entry, never trusted from an earlier pass).
   "Recipe-runnable is not unattended."
5. **A durable phase marker makes the run resumable.** The declared var set the recipe maintains IS the
   phase marker (observable, not inferred), together with state assertions; a re-run of a point-of-no-return
   phase whose witness already shows it done is refused. A recipe is an ordered list of waldo phases
   sharing one marker file.

Also adopted from the design: carry the COMPLETE var set on every apply (our `plan_env`), never rely on
committed defaults; assert a standing flag at the top of every phase it must hold (their OQ-2).

## What cassian's .sh recipes add (read 2026-10-12: `openbao-vault-apply.sh`, `vault-apply.d/00-lib.sh`,
`81-p8-revoke.sh`; the other fragments and stage-a.d are not read)

The recipe layer (W1060) is concrete in these files:

1. **One phase per invocation.** The driver sources every fragment and dispatches `status | guard | p0..p10`:
   "run ONE phase at a time". `status` reads the world and says which phase is done; `guard` runs the
   clean-start refusals alone. A run is never "all phases".
2. **The durable phase marker is a file the recipe writes** (`write_tfvars`: the five gate variables) and
   reads back (`tfvar`), not a re-derived judgement; each phase begins by ASSERTING the standing flags it
   needs (`assert_deploy_renewer_true`, `assert_tpm_unseal_true`) and refuses when the marker disagrees.
3. **The point-of-no-return confirmation is a challenge-response, not a y/n.** P8 requires
   `P8_CONFIRM_REVOKE=<the genesis root's accessor>`: a value read off the very thing about to be destroyed,
   so only someone who looked can supply it. The waldo confirmation token is therefore a *named reading* the
   operator must reproduce, not a typed phrase.
4. **Entry re-assertion.** P8 re-reads the token's policies (scoped, not root) and re-proves the renewer
   heartbeat at its own entry; it does not trust P5's earlier pass.
5. **A code-contract witness.** P8 greps the *comment-stripped* deployed fragments for the code that makes
   the phase safe (`revoke -accessor`, reads the genesis Secret, confirm-dead lookup, a replay-gating
   helper). If the code is absent the phase halts with the named residue: "authored to its constructible
   floor". A phase may exist and refuse until its precondition is in the source, saying exactly what is
   missing; comments are stripped so the check cannot match prose that describes the bug.
6. **`advances` is a strictly-greater numeric comparison, with a mangled-read refusal.**
   `witness_renewer_heartbeat` requires the heartbeat `ts` to be numeric before AND after and the after
   value to be strictly greater, refusing a non-numeric read rather than reasoning about it. W1057's
   `advances` is "differs"; a numeric `increases` kind is W1063.
7. **A failure inside a witness is distinguished from a failed condition.** A Job that did not complete in
   120 s is a warning while the heartbeat advance is "the real witness": the witness that matters is
   named, and weaker signals are demoted to notes.

## Cards (atomized)

W1053 stays the umbrella. Children are minted from this note; each is one landable unit with its own
tests and warrants, and none commits until the commit gate is usable again (W1052).
