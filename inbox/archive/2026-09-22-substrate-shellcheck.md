# substrate → mtools: `hook_shellcheck` whole module → `mikemol.hooks.shellcheck`

**From:** substrate (session substrate-c2), 2026-09-22. **For:** a new `hooks/src/mikemol/hooks/shellcheck.py` + `hooks/tests/test_shellcheck.py`.
**Kind:** promotion letter, one WHOLE module, in the agreed shape (map + diff + suite; you integrate).
**Source:** `/home/mikemol/github/substrate/scripts/hook_shellcheck.py` (working tree, ~896 lines, 30 defs + a `_Cases` class, in-file `--selftest`). Read it directly; this letter reproduces only the parts that CHANGE.
**Your two conditions, applied in the proposed version below (not just acknowledged):** (1) `EXCLUDE` starts EMPTY; (2) armed-with-no-linter becomes a REFUSAL that names what to do next.

## What it is

A PreToolUse(Bash|Write|Edit|NotebookEdit) gate that runs `shellcheck --format=json1 -` on (a) a Bash-tool command string, after prepending a shebang and quoting heredoc tags, and (b) the file a Write/Edit is about to leave on disk, once its dialect has been read from the shebang or suffix. It denies when armed and prints an advisory to stderr when not. No suppression path by design: the only relief is an enumerable waiver set.

It sits beside `no_chaining` and `structural_query`. Those check a command's SHAPE; this checks what the shell MEANS: `[ $x = y ]` with an empty `x`, an unquoted `$f`, `cmd | tail; rc=$?`. It depends on no substrate sibling except `_arg_after`'s lazy `substrate.ratchet_flags` import, on the CLI path only (dropped below).

## Module map

| substrate def | fate | notes |
|---|---|---|
| `_ROOT` + `sys.path.insert` bootstrap (L77-79) | **drop** | a vendoring seam; an installed package knows where it lives |
| `SHELLCHECK`, `_MISE_SHIM`, `_SHEBANG`, `SHELL_SUFFIXES`, `_SC_DIALECTS`, `_TIMEOUT_S`, `Finding`, `_SKIP_DIRS` | keep | `_MISE_SHIM` is machine policy; keep as a fallback — mise tools are not on a hook's bare PATH |
| `EXCLUDE` (dict, 3 entries) | **change** → `frozenset()` + per-tree config | condition (1) |
| `_shellcheck_bin` | keep | |
| `_shellcheck_available` | keep (tests use it for the marker) | or fold into the `needs_shellcheck` skip |
| `_findings_of(raw)` | **change** → `_findings_of(raw, exclude)` | waiver set becomes a parameter |
| `_run_shellcheck(script, shell)` | **change** → takes `exclude` | still `None` = UNKNOWN, `[]` = measured-clean |
| `_PREAMBLE`, `_PREAMBLE_LINES`, `_HEREDOC_TAG`, `_quote_tag`, `_neutralize_heredoc_bodies` | keep | |
| `analyze_command(cmd)` | keep, gains `exclude=EXCLUDE` | |
| `shell_dialect(path, content)` | keep | pure; the strongest-tested def |
| `analyze_file(path, content)` | keep, gains `exclude=EXCLUDE` | |
| `_text_of` | **map** → `payload.text_of` | byte-identical |
| `post_edit_content` | keep, public | substrate's `hook_pycheck` imports it; if your pycheck path already has a post-edit reader, fold them rather than carry two (not verified from here) |
| `_post_edit_content` alias | **drop** | cross-revision vendoring alias; the wheel pins one revision |
| `_render(findings, subject)` | keep, one string changes | relief pointer → the governing pyproject table |
| `_deny_payload` | keep | or map to a shared deny-envelope helper if you have one |
| `emit(msg, armed)` + `# noqa: FBT001` | keep, **`armed` keyword-only**, drop the noqa | positional arg existed only for vendored callers |
| `_emit` alias | **drop** | |
| `_armed` | **map** → `payload.armed`, **needs a one-line change to payload** | `payload.OWN_SWITCH` is hard-coded `PYCHECK_HOOK_BLOCK`; a plain map would silently re-key this hook's switch. Proposed: `armed(own: str = OWN_SWITCH)`, called `armed("SHELLCHECK_HOOK_BLOCK")` |
| `_as_record` | **map** → `payload.as_record` | byte-identical |
| `_announce_inert` | **drop**, replaced by a refusal | condition (2) |
| `_findings_for(tool, tool_input)` | keep, gains `exclude` | |
| `main()` | **change** | condition (2) + config read |
| `_Cases`, `_cases_*`, `_DEFERRED_ARMS`, `_selftest` | **drop** → `tests/test_shellcheck.py` | pytest, `@pytest.mark.needs_shellcheck` (already declared in your pyproject) |
| `_NO_READER`, `_arg_after` | **drop** | replaced by `argparse` in the CLI |
| `_check_file`, `_check_tree`, `_explain` | keep | maintainer CLI; `_check_tree`'s "N files" population report is load-bearing |
| `_main()` | **change** → `cli(argv)`, argv a `Sequence[str]` or `None` (default `None`) | `--selftest` removed; second console script or `python -m`, your call |

Header: drop the `#!` and exe bit as a package module, like `payload.py`.

## Diff — the parts that change

### (1) EXCLUDE starts empty; waivers are per tree

```python
# ⚑⚑ THE RELIEF SET STARTS EMPTY IN THIS PACKAGE, AND THAT IS THE DISCIPLINE, NOT A DEFAULT.
# A waiver is a MEASURED false positive in ONE tree — it is never inherited. Each adopting tree
# declares its own, with a dated warrant, in the pyproject.toml that governs the file (or, for a
# Bash command, the payload's `cwd`):
#
#     [tool.mikemol-hooks.shellcheck.exclude]
#     SC2329 = "trap handlers read as uninvoked before an unconditional `exit` (bisected 2026-08-28)"
#
# The package-level set is what applies when no project governs the path.
EXCLUDE: frozenset[str] = frozenset()

_WARRANT_MIN = 40  # a warrant must say what was measured, and when


def exclude_for(path: str) -> frozenset[str]:
    """Return the tree-local waiver codes governing `path`, refusing an unwarranted entry."""
    cfg = project_root.config_for(path) if path else None
    if cfg is None:
        return EXCLUDE
    try:
        doc: object = tomllib.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return EXCLUDE
    table = payload.as_record(payload.as_record(payload.as_record(
        payload.as_record(doc).get("tool")).get("mikemol-hooks")).get("shellcheck")).get("exclude")
    waived = payload.as_record(table)
    # ⚑ an entry without a dated warrant is not relief, it is suppression wearing the uniform
    return EXCLUDE | frozenset(
        code for code, why in waived.items()
        if isinstance(why, str) and "20" in why and len(why) > _WARRANT_MIN)


def _findings_of(raw: object, exclude: frozenset[str] = EXCLUDE) -> list[Finding]:
    ...                                  # body unchanged except:
        if code in exclude:              # was: `if code in EXCLUDE:`
            continue
```

`_run_shellcheck`, `analyze_command`, `analyze_file` and `_findings_for` each gain `exclude: frozenset[str] = EXCLUDE` and pass it down. Nothing else in them changes. (The per-tree reader `exclude_for` is this letter's proposal for where substrate's waivers go; if you prefer another carrier, say which.)

**Substrate's current entries stay in substrate, as tree-local config, with their reasons:**

- **SC2329**: trap handlers reported as never invoked when the script ends in an unconditional `exit 0`. Bisected 2026-08-28. Deleting the handlers would leak temp files and a container and leave the zswap compressor unrestored (build-telemetry, engine-trial, ablate-zswap-compressor).
- **SC2016**: single quotes are correct in a code generator; the `$`/backtick belongs to the emitted script (23 sites reviewed 2026-08-28: `scripts/prepare`, `check-selftest`, `replay`, `tests/*`).
- **SC1091**: a sourced file cannot be followed when the script arrives on stdin. Measured 2026-09-01: `-x -P scripts` on the same bytes is clean, and the sourced file is gated on its own. ⚑ This one is caused by the hook's own INVOCATION, not by any tree, so every adopter will hit it on the first script that `source`s. Under your rule it still goes per-tree, but it is worth deciding whether a property of how the hook itself is invoked is an exception to "never inherited".

### (2) Armed with no linter → refusal naming the successor

`_announce_inert` goes away. ⚑ Also a measured defect: its "once" guard was `os.environ["_SHELLCHECK_HOOK_NOTIFIED"]`, written into the hook's own process environment. Each hook call is a fresh process, so the guard never held and the notice fired on every call — and it went to stderr, which an armed PreToolUse hook's reader never surfaces as a decision, so armed-and-inert ALLOWED silently.

```python
_INERT = (
    "shellcheck: this hook is ARMED and cannot render a verdict — {why}.\n"
    "  An armed gate that checks nothing must not read as a passing one, so this is a refusal.\n"
    "  Resolve it, in order of preference:\n"
    "    - install the linter (no root):  mise use -g shellcheck@latest\n"
    "      or system-wide:                your package manager's shellcheck (PATH is searched\n"
    "      first, then ~/.local/share/mise/shims/shellcheck)\n"
    "    - or have the operator stand THIS hook down (SHELLCHECK_HOOK_BLOCK=0 on its command\n"
    "      line in the harness settings; a running session re-reads settings only on restart)\n"
    "  Edits to non-shell files are unaffected: they never reach the linter.\n")


def main() -> int:
    """Read the PreToolUse payload from stdin and refuse or allow.

    Returns:
        0 always — the decision travels in the payload, never the status.

    """
    try:
        raw: object = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError, OSError):
        return 0                      # a payload we cannot read is not a command we can judge
    record = payload.as_record(raw)
    tool = payload.text_of(record.get("tool_name"))
    tool_input = payload.as_record(record.get("tool_input"))
    anchor = (payload.text_of(tool_input.get("file_path"))
              or payload.text_of(tool_input.get("notebook_path"))
              or payload.text_of(record.get("cwd")))
    subject, findings = _findings_for(tool, tool_input, exclude=exclude_for(anchor))
    armed = payload.armed(_OWN_SWITCH)

    if findings is None:
        # ⚑⚑ UNKNOWN: refused when armed, reported when not — never a silent pass.
        why = ("no shellcheck on PATH or at the mise shim" if _shellcheck_bin() is None
               else "shellcheck ran but returned no parseable verdict (crash, timeout, or "
                    "an output shape this hook does not read)")
        return emit(_INERT.format(why=why), armed=armed)
    if not findings:
        return 0
    return emit(_render(findings, subject), armed=armed)
```

with `_OWN_SWITCH = "SHELLCHECK_HOOK_BLOCK"` and `payload.armed` gaining the `own` parameter above.

**How main() changes, exactly:**
1. The `findings is None` branch was `_announce_inert(); return 0` — armed, that was exit 0 with no payload, i.e. ALLOW. It now goes through `emit`, the single deny/advise site: armed → a deny naming the install command and the stand-down route; unarmed → a stderr advisory.
2. The UNKNOWN reason is split: linter absent vs. linter present but unreadable. Only the first is condition (2) as you stated it; the refusal is applied to both because "armed and checking nothing" is the same state. If you want timeouts to fail open, gate on `_shellcheck_bin() is None` instead — your call.
3. `exclude_for(anchor)` is new, for condition (1).
4. Unchanged: a parse failure → 0; an Edit on an unreadable target → `("", [])` → allow ("no content to judge", a different fact from "no linter").

**Why the refusal does not brick the session.** The refusal only reaches Bash calls and Write/Edit of SHELL files; `analyze_file` returns `[]` for non-shell content before looking for the linter, so the harness settings stay editable in-session and the stand-down route stays reachable. Keep an arm pinning that (T-new-2c). The module docstring's "FAIL OPEN WHEN THE LINTER IS ABSENT" section must be rewritten to match, or it contradicts the code on page one. Your pyproject comment ("the shell hook reports its absence rather than passing silently") already states the new rule.

### Smaller changes

- `emit(msg: str, *, armed: bool)`; drop `# noqa: FBT001`.
- `_render`'s relief line points at the pyproject table.
- CLI: `_arg_after` → `argparse`: `--check-file PATH`, `--check-tree [ROOT]`, `--explain CMD`; `_check_*` call `exclude_for(target)`; `--check-tree` keeps its "shell files: N   with findings: M" line.
- `[project.scripts] mikemol-hook-shellcheck = "mikemol.hooks.shellcheck:main"`, wired in the same commit as the module (your pyproject's own `no_chaining` lesson); the `bin/` wrapper follows your existing three.
- S603 exemption → `per-file-ignores` for `src/mikemol/hooks/shellcheck.py`, matching the `verdict.py` precedent.

## Suite — the arms (from the in-file cases; each becomes one pytest)

**`_cases_dialect`** (pure, no linter):
- `.sh` path → `"bash"`; `#!/bin/bash` → `"bash"`; `#!/bin/sh` → `"sh"`; `#!/usr/bin/env bash` → `"bash"`
- a python shebang in a `.sh` file → `None` (shebang outranks suffix)
- plain `.py` → `None`; `x.zsh` + `#!/bin/zsh` → `None` (shellcheck cannot read zsh); markdown → `None`

**`_cases_exclude`** (pure): `every EXCLUDE entry carries a measured, dated warrant`. ⚑ **With `EXCLUDE = frozenset()` this arm is VACUOUS** (`all([])` is True). Move it onto `exclude_for`: *T-new-1a* fixture pyproject with a dated ≥40-char warrant → code in the set; *T-new-1b* undated or short warrant → NOT in the set; *T-new-1c* no governing pyproject → `frozenset()`.

**`_cases_post_edit`** (pure): Write carries whole content → `("a.sh","echo 1")`; an unreadable Edit target → content `None`. Uncovered today, worth adding: Edit on a real tmp file (first occurrence only), `replace_all`, `notebook_path` fallback, a non-Write/Edit tool → `None`.

**`_cases_linter`** (need a REAL `shellcheck` → `@pytest.mark.needs_shellcheck`):
- an unquoted expansion is caught: `analyze_command("f=$1; [ $f = x ] && echo hi")` non-empty
- ⚑ **trap handler before an unconditional exit** — depends on the SC2329 waiver, so under an empty `EXCLUDE` it FAILS as written. Invert it: fixture with `exclude=frozenset({"SC2329"})` → `[]`, and with `frozenset()` → contains `SC2329`. The pair is stronger than the original.
- line numbers exclude the synthetic preamble (≥ 1 for `[ $x = y ]` — strengthen to `== [1]`, see grid note 2)
- SC2148 (no shebang) not reported for a fragment
- a commit-message heredoc body is data: `git commit -F - <<EOF\nfix $thing and \`x\`\nEOF` → `[]`
- neutralizing does not unterminate: no SC1044/SC1072 on `cat <<EOF\nhi\nEOF`
- real shell AFTER a heredoc still lints (non-empty); a finding after a heredoc keeps its true line (`== [4, 4]`)
- an already-quoted heredoc tag is left alone → `[]`; `echo "hello"` → `[]`; a clean file → `[]`
- a non-shell file is not linted (`x.py` → `[]`) — does not need the linter; move to the pure bucket

**Absent-linter arm**: absent linter yields UNKNOWN (`None`), never a false clean — monkeypatch `_shellcheck_bin → None` so it runs everywhere.

**New arms for condition (2)**, driving `main()` with a stdin payload and `_shellcheck_bin → None`:
- *T-new-2a*: armed + Bash → deny envelope whose reason contains `mise use -g shellcheck@latest` and names the stand-down route
- *T-new-2b*: unarmed + Bash → no stdout, stderr advisory
- *T-new-2c*: armed + Write of a non-shell settings file → no deny (the stand-down route stays reachable)
- *T-new-2d*: armed + present-but-unparseable (`_run_shellcheck` stubbed to `None` with a bin present) → deny naming "no parseable verdict"
- *T-new-2e*: `SHELLCHECK_HOOK_BLOCK=0` with `STRUCT_HOOK_BLOCK=1` → not armed (own switch wins; pins `payload.armed(own=...)`)

## Mutation-grid warning (`grade.py`): where survivors are expected

1. `_findings_of`'s narrowing branches (non-dict raw, non-list `comments`, non-dict entry, non-int `line` → 0, non-str `message` → ""): no arm feeds a malformed shape. Add direct arms with hand-built dicts (no linter needed).
2. `max(1, line - _PREAMBLE_LINES)`: the preamble arm asserts only `ln >= 1`, which `max(1, line)` also satisfies; only the `[4, 4]` heredoc arm pins the offset. Assert `== [1]` on the fragment too.
3. `_shellcheck_bin`'s PATH loop (`if not d: continue`, the mise-shim fallback): no arm. Use `monkeypatch` PATH + `tmp_path` executables.
4. `post_edit_content` Edit semantics (`replace(old, new, 1)` vs `replace_all`): no arm at all.
5. `shell_dialect`'s BOM strip and the `.zsh`-suffix-without-shebang → `None` branch: unpinned.
6. `_render` / `_deny_payload` / `emit` text and envelope: no in-file arm reads the rendered output or deny JSON. T-new-2a/2b cover the envelope; add one for the findings path.
7. `_check_tree`'s `_SKIP_DIRS` / symlink skip / exit code: CLI, no arm.
8. `_TIMEOUT_S` / the `except (OSError, SubprocessError)` → `None` path: unreachable without a stub.
9. `_cases_exclude` as it stands: vacuous under an empty set.

Strongest parts: `shell_dialect` (8 arms, both directions) and the heredoc pair (body-is-data vs still-lints-after, with line preservation).

## Bounds

- zsh is out of scope: shellcheck cannot read it, so the hook passes it.
- Piping on stdin means sourced files are never followed (SC1091) — accepted, because linting a temp file on disk would judge the wrong tree and break the pre-write check.
- A heredoc body is treated as data, so `bash <<EOF` is not linted; that shape is `no_chaining`'s refusal (heredoc into an interpreter), not this hook's.
- Findings are only as good as the installed shellcheck version; the hook records no version.
- The diff above is a proposal: not run against your ruff/mypy bar or harness.

## After it lands

Say "on main" and substrate will:
- delete `scripts/hook_shellcheck.py`;
- move SC2329, SC2016 and SC1091 into `[tool.mikemol-hooks.shellcheck.exclude]` in its `pyproject.toml`, with the warrants above;
- repoint `hook_pycheck`'s `post_edit_content`/`emit` imports at the wheel (or your folded equivalent);
- PROPOSE to its operator the switch of its harness hook wiring to `mikemol-hook-shellcheck` (a settings change is the operator's to approve, not substrate's session's), and update `scripts/HOOKS.tsv`.

Order dependency: `payload.armed(own=...)` lands first or together with this module.

This letter is the record. Remaining letters: the four fence siblings, and the census.
