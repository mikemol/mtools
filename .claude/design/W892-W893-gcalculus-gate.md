# W892 and W893: gcalculus' two asks, as designs (2026-10-09)

Source: `inbox/2026-10-09-gcalculus-gate-stages-env-and-hook-probe.md` (archived once answered). Both
asks block `gcalculus:W91` (its bazel pre-commit). Operator framing for item 2: ask how to solve the
problem, not how to run the test outside the sandbox.

## W892 (gcalculus:W222): a gate stage that can import the pinned engine

Problem. `gate_stages(stages, data, suite)` gives a stage a script, args and data. Five of
gcalculus' 775 gcalc leaves import paperkit's `labelmap`, found through `PAPERKIT_ENGINE`; only
`paperkit_gate` (via `paperkit_gate_main.py`) provides that and the checkout on `PYTHONPATH`.

Mechanism, not a one-off. The engine environment is built in `paperkit_gate_main.main` inline. It is
one fact (PYTHONPATH = the checkout above the engine package; `PAPERKIT_ENGINE` = the package dir;
`PAPERKIT_SCRATCH` = `TEST_TMPDIR`), so it becomes ONE function and both runners call it:

| slice | card | what |
| --- | --- | --- |
| 1 | W895 | `rules_py/engine_env.py`: `engine_env(engine, environ) -> dict`, a test with a stand-in engine tree; `paperkit_gate_main` calls it. |
| 2 | W896 | `rules_py/engine_stage_main.py`: `--engine=<gate.py rootpath> --script=<rootpath> [-- args]`; refuses an undeclared input like `paperkit_gate_main`; runs the script with `sys.executable` under `engine_env`; returns its status. |
| 3 | W897 | `gate_stages`: the stage tuple takes an optional 4th element, a dict `{engine_repo, engine_files, env}`. With `engine_repo` set the stage's `main` is `engine_stage_main`, `args` gain `--engine/--script`, and the engine files join `data`; `env` passes to `py_test`. A stage without the dict is byte-identical to today. |
| 4 | W900 | the reply to gcalculus naming the slices and how to call it. |

Per stage, not per call: gcalculus needs the engine in ONE stage (the sweep); handing it to every
stage would put the engine's files in every stage's cache key.

Open (decided, revisit if wrong): `PYTHONPATH` stays the checkout only, never the package dir
(`paperkit_gate_main`'s own measured reason: the engine's flat `config`, `layout`, `bib` would
shadow a check's own).

Witness plan. Slice 1-2 are plain pytest in `rules_py` (the root `//:` test targets run them).
Slice 3 needs a load-and-run witness: a sample `gate_stages` with an engine stage over a stand-in
`pinned_files`-shaped repository under `rules_py/testdata`, built by `bazel test` in the gate.

## W893 (gcalculus:W223): is "an adopted hook still denies when fired" mtools'?

Answer: yes, and mtools' coverage is PARTIAL, which is the reason to build the tool rather than
argue the boundary.

What exists (read from the tree, 2026-10-09):
- `hooks/tests/test_bin_launchers_argv.py`: every launcher execs its console script with the
  harness's arguments, and an absent venv denies a gate (explicit deny JSON, exit 0), both via a
  stand-in venv, hermetically.
- `hooks/tests/test_no_verify.py::test_the_installed_console_script_denies_when_armed`: one real
  end-to-end deny, for no-verify only, and it `pytest.skip`s when the console script is not
  installed, so in a sandbox that lacks the venv it proves nothing.
- Nothing fires a launcher from a FOREIGN cwd, and nothing fires the other gates' deny payloads.

Mechanism: `mikemol-hooks-probe` (W898), a console script, not a gcalculus-local test:
- a table `gate -> (payload, expected decision)` for no-verify, no-chaining, shellcheck and
  structural-query (data, one place);
- an argv template for the launcher with an `{entry}` placeholder and no shell, so an adopter
  points it at its own `tools/hook {entry}` and mtools points it at `hooks/bin/{entry}`;
- runs each row from the repo root and from a temporary foreign cwd; a row passes only on
  `permissionDecision: deny`; a row that cannot run (absent launcher) is a FAILURE, never a skip;
- exit 0 only when every row denied, one line per row.

W899 runs the probe hermetically in `//hooks` (stand-in venv whose python3 execs the real entry
modules, plus the absent-venv case), replacing the skip-able arm. Then gcalculus pins the mtools
commit carrying the probe and drops its `concepts_45.py` copy; an adopter's own run is
`mikemol-hooks-probe --launcher 'tools/hook {entry}'`.

Nothing here edits settings.json or any hook wiring.
