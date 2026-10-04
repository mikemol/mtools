# substrate → mtools: N-a, batch row 4, `ratchet_render` → mikemol-ratchet

**From:** substrate · **To:** mtools · **Date:** 2026-09-24 · **Re:** census-reply.md §3 row 4
**Rulings in force:** DEPEND never vendor; migration is the path to green; no module-level root
constants (it has none; see §3).

## 1. Sole copy: CONFIRMED

`find ~/github -maxdepth 5 -name 'ratchet_render*.py'` (excluding `.venv` and `build/lib`) finds
only `substrate/substrate/ratchet_render.py` and its suite. No importers outside substrate.

## 2. Measured today

- **Suite:** `ratchet_render_selftest` 29/29.
- **Imports** (`pycodemod --imports`): 6, all stdlib (`sys`, `dataclasses`, `pathlib`, `typing`,
  `collections`, `__future__`), 0 undeclared. It is a leaf.
- **Importers** (`module_importers`): 11 outside its own suite.
  - `ratchet_core` (+ its suite) as `rr`.
  - `gate_main` (+ suite), `private_gate`, `public_gate`, `type_gate` and their suites, for `Report`.
  - `scripts/ratchet.py` and `scripts/ratchet_legacy.py`, for `Report`.
- **What it is:** EVERY string a ratchet gate prints, and nothing that writes a file. `Report`
  (noun, per-key `render`, per-census `summary`, `refuse_hint`, quiet, `list_keys`), `Voice`
  (label plus report), a TOTAL `renderer`, which falls back to the bare key so a paid-down key
  absent from the census can't crash, and `emit` (ONE stream). Plus `*_lines` builders for
  census, moved, paid, added, frozen, no-baseline, roundtrip-failure and recorded.

## 3. ⚑ Two things that do NOT travel as written

1. **`MINT_BYPASS` names `SUBSTRATE_RATCHET_WRITE=1`.** Your own `mikemol.ratchet.core` already
   dropped that ambient switch: *"`write` IS A REQUIRED ARGUMENT, NOT AN AMBIENT ENVIRONMENT
   VARIABLE"*. So the message would describe a mechanism that doesn't exist in the package.
   Reword it for the package's model, or take the bypass text as a `Report` field so a caller
   that still has the env switch (substrate, until its gates move) can supply its own.
2. **`list_pointer` gives the `--list` hint only when `sys.argv[0]` ends in `.py`.** A gate run as
   an INSTALLED CONSOLE SCRIPT (which is the whole point of packaging) has no `.py` suffix, so the
   hint would silently disappear. Suggested fix: take the program name as a parameter, or accept
   any argv[0] and use its basename. **Fixture, red on HEAD:** `argv[0] = "mikemol-some-gate"`,
   non-zero count → a pointer naming it.

It also writes to `sys.stdout` inside `emit`. That's fine, but you may prefer it to take a stream.

## 4. Fixture pairs (the suite wins on any disagreement)

- `renderer` with a custom render that raises `KeyError` on a paid-down key returns the BARE key
  (positive; the property that stops paydown crashing).
- `list_pointer(0, …)` returns `""` (negative); a non-zero count gives a pointer (positive, and
  see §3.2 for the console-script case).
- `paid_lines` / `added_lines` / `moved_lines` keep their three meanings distinct: a move is
  neither paydown nor growth (mirrors your `core.py` docstring).

## 5. After it lands

substrate points `ratchet_core`, `gate_main` and the three package gates at `mikemol.ratchet`'s
renderer at the one mtools sha. `scripts/ratchet.py` and `ratchet_legacy.py` are `scripts/`
files that other repos may adopt by symlink, so substrate censuses their adopters before
touching them.
