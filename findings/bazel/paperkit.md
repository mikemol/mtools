# Bazel findings — paperkit

**Repo:** paperkit · **Date:** 2026-09-05 · Companion to `mtools.md`.
Every figure re-derived here; where one came from another repo it is marked and attributed.

---

## 1. ⚑⚑⚑ NOBODY IS ON THE SANCTIONED CONFIGURATION, AND THE HALVES ARE COMPLEMENTARY

The sanctioned configuration is **remote BES + cache, no local fallback**. MEASURED across two
repos today:

| repo | BES | executor / cache | on sanctioned config? |
|---|---|---|---|
| **paperkit** | `--bes_backend=grpc://127.0.0.1:31985` | **none** | ✗ — BES without executor |
| **cassian** | **none** (grep over `.bazelrc` + `.githooks/pre-commit`: zero hits) | `--remote_executor=…:31985` | ✗ — executor without BES |

⚑ **Two repos hold complementary halves of one configuration and each believed it was configured.**
Neither could have discovered this alone: paperkit's flags look right in isolation, and so do
cassian's. It surfaced only when a third party asked one repo to send the other its docs.

**Measured off the LIVE PROCESS, not the config file** — `ps -o args=` on the running `//:hook`:

```
--config=mutant --bes_backend=grpc://127.0.0.1:31985 --bes_upload_mode=fully_async
build:mutant --experimental_use_hermetic_linux_sandbox      <- ONE LINE. That is the whole config.
```

⚑ **`--config=mutant` pulls in neither `cas` nor `remote`.** The name suggested a mutation-sweep
configuration carrying the remote setup; it carries a sandbox flag. *Reading the config file would
not have shown this — the flags arrive from three places (rc config, `PAPERKIT_BES` in
`.githooks/local.env`, the hook's own command line) and only the process has all three.*

## 2. ⚑⚑ THE DOCS DO NOT EXIST — a capability nobody can find is absent

The operator directed paperkit to cassian for RBE/BES documentation. Cassian looked rather than
answering from memory: `find docs/ -iname '*rbe*' -o -iname '*buildbuddy*' -o -iname '*bes*' -o
-iname '*remote*'` returns **two plans and no how-to**. The configuration lives in `.bazelrc`
comments and in cross-session messages.

**Consequence, measured rather than argued:** cassian **cannot answer** what the invocation-record
interface gives, because they have never run BES. The one question that most needed an experienced
answer had no one to answer it, and neither party knew that until asked.

## 3. THE FLAG SET (cassian's, read from their `.bazelrc`; attribution caveat below)

```
build:remote --remote_executor=grpc://127.0.0.1:31985
build:remote --remote_instance_name=cassian-gate
build:remote --extra_execution_platforms=//tools:cassian_gate_platform
#            NO --remote_local_fallback  — absent entirely, not set false
```

- **Executor only**, no separate `--remote_cache`; the executor's CAS is what it gets.
- **`--remote_local_fallback` is ABSENT, not false.** Their comment: *"an action routed to RBE runs
  ON the executor or FAILS LOUDLY, never degrades to a local escape"*, with the cost stated —
  `--config=remote` hard-depends on the executor being up.
- **`--remote_instance_name` differs per repo** (`cassian-gate` vs paperkit's `paperkit`), so the
  CAS partitions differ. Consistent with linux-sources' finding that it partitions at the server's
  **storage layer** while **not** being in the action key — both true, and mtools and linux-sources
  initially got this wrong in opposite directions.

⚑ **ATTRIBUTION CAVEAT, carried because it was volunteered against interest.** That line's comment
cites an *"(operator ruling 2026-09-04)"*. linux-sources swept 399 files / 173,842 envelopes and
found **zero** operator statements behind it — the input said *"the operator picks the fix from your
per-arm data"*, the output said *"must be removed under the ruling"*. **The input said the operator
WILL decide; the output said they HAD.** The decision is right on its merits and three repos'
independent reasoning corroborates it; **the attribution is unwitnessed.** *(Checked here: paperkit's
`.bazelrc` makes no operator attributions — `grep -nE "operator (ruling|said|decided|asked)"`
returns nothing.)*

## 4. ⚑⚑ `--remote_local_fallback` IS THE THING THAT HIDES A MISCONFIGURATION

paperkit sets it on **both** remote configs (`.bazelrc:247`, `:283`), justified as *"a cache/executor
that is DOWN must not fail the build."*

**MEASURED by linux-sources:** `--config=remote` died at **analysis** for weeks — a bare
`platform()` with no `constraint_values` satisfies no toolchain — and returned **GREEN with zero
remote actions** the entire time. *The fallback was not a safety net; it was the thing hiding a total
failure.*

> **A flag that degrades silently converts a configuration error into a passing build.**

⚑ And the class is self-applying: the fallback is precisely what would have kept paperkit from
noticing it was not on the sanctioned config. *(paperkit has no `platform()` targets at all, so the
bare-platform instance cannot bite here — but the class is about the fallback, not the platform.)*

## 5. ⚑⚑⚑ EXIT-CODE-AS-VERDICT — four faces, all measured in one session

Reading a build's outcome from a wrapper's status rather than the payload's own verdict:

| face | measured |
|---|---|
| wrapper 0 over payload FAIL | notification said `exit code 0`; log line said `[pre-commit] FAIL: hook-index` |
| wrapper 0 over **no verdict line at all** | run ended with neither `ok:` nor `FAIL:` emitted |
| pipe-tail | `timeout 300 … \| tail -5` → `Terminated`, exit **0** from `tail`, no artifact built |
| **static log read as finished** | log quiescent → declared complete; run was mid-analysis and ran **8 more minutes** |

⚑ **The fourth is the dangerous one and it is unfixable by better tailing:** *a log going quiet is
indistinguishable from a log that ended.* Acting on it, paperkit **edited `tools/wheel.py` 70
seconds into a live `//:hook`** — the input-dependency-modified corruption class, self-inflicted,
by the session that had spent the day measuring that class.

**The correct liveness test is not the log and not `pgrep -c`** (which returned 0 at the top of the
tick, correctly, before the build was launched) — it is `ps` on the **pid holding the Bazel server
lock**, which the server names in its own "Another command is running" message. ⚑ **A queryable
invocation record with a TERMINAL STATE fixes this by construction rather than by discipline**,
which is the argument for the sanctioned config that has nothing to do with speed.

## 6. A STALE CLAIM CARRYING ITS OWN VERIFICATION

`.githooks/local.env` held:

> `# indirection is right and held a dead value. BES (:1985) did NOT move; verified open.`

MEASURED: **`:1985` closed, `:31985` open, `:31080` open.** The endpoints moved with the k3s
migration and the comment did not.

⚑ **This is the worst variant of the comment-that-outlived-its-code class yet catalogued: the other
instances were assertions; this one ASSERTED ITS OWN CHECK.** A reader applying *"verify, don't
trust"* sees the word **verified** and stops. *(cassian's framing.)* Corrected in place, with the
correction visible rather than swapped.

## 7. ⚑ `Ζ·cellvenv·race` — a concurrency defect the gate found in the gate's own new code

Four `FileNotFoundError` tracebacks from four different cells:

```
FileNotFoundError: '.../execroot/_main/.cellvenv/lib'
  venv/__init__.py  clear_directory -> shutil.rmtree -> os.rmdir
  tools/wheel.py:96  venv.EnvBuilder(..., clear=True).create(vd)
```

Every cell is handed the same `"$PWD/.cellvenv"` and **sandboxed actions share an execroot**, so
concurrent cells race and `clear=True` clears a tree another is walking.

**⟨P, F, δ⟩ — both arms, same δ (6 concurrent `install` calls at one path):**

```
F  pre-fix code   ->  2/6 fail   (also surfaced a second face: PermissionError on bin/Activate.ps1,
                                  a concurrent write into a tree another process is clearing)
P  fixed code     ->  0/6 fail, marker present, zero leftover tmp dirs
```

**Fix:** build to `.cellvenv.<pid>.tmp`, write a `.pk-complete` marker, `os.rename` to claim the
shared name; the loser of the race discards its own copy rather than clobbering a venv in use.
`install` is content-determined (same wheel + deps → same tree), so reuse is sound — *action
idempotency applied to the action's own scratch space.*

## 8. FIGURES — and a filter that matters more than the figures

`"input dependency modified during execution"` over paperkit's transcript corpus:

```
91  -> 32 -> 24        (each correction itself under-corrected)
CURRENT: 24 occurrences, 6 distinct days, 15 pre-executor-cutover / 9 post
```

⚑⚑ **The filter is the finding.** Filtering on record **type** `user` still admits **peer messages
and system reminders quoting the phrase** — so the census's own correspondence about the number
inflated the number, **twice**. The correct predicate is **`toolUseResult` present on the record**.

> **A count over a corpus that includes the discussion of the count is a feedback loop — and the tell
> needs no knowledge of the right answer: the number DRIFTS UNDER RE-QUERY.**

⚑ Cite the filter, not the number. Four repos quoted 91 and then 32 without re-deriving either;
this is `mtools.md`'s Rule 9 (*cross-vantage review checks REASONING, not INPUTS*) with a third and
fourth instance.
