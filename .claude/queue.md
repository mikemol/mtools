# mtools drain queue (W24)

This is the long form. W24's `next_bounded_step` points here, so the payload carries a short
pointer and the standing rules are never crowded out.

1. DONE 000785b + 01771e0 (the leftovers below are fixed in 01771e0): the pathsforward fix bundle. summit was told, and its W50b repair is unblocked.
   Leftovers: a trailing `.` on an evidence path is not trimmed; `--queue` and the mirror still
   list in file order.
2. DONE f7a4b80: the root scripts are linted and typed, and have a warrant home (root pyproject,
   //:ruff, //:mypy); the gate refuses orphan or unwarranted warrants (13 check lines added,
   every population at 0); a symlink is never a distribution; setup.sh makes the root .venv.
3. DONE b63b548: `git_scrubbed` is defined once, in `git_env.sh`, and sourced by all three
   launchers; a missing file stops the run. mutate_runner KEEPS its local filter (measured: fence
   is importable only in fence's venv). OPEN: whether every distribution's dev deps include fence.
4. DONE 415d532 + d55dbd6: the ratchet "cannot census" refusal (exit 2); a relative RUFF_BIN is
   anchored; the gate and preflight name exit 2 apart from a new key; the copied phrases are
   fixed.
5. DONE 39d81b1: MD041 skips the SPDX header. The root README got its header, by the operator's
   ruling (header only, no title), so its MD041 for opening with prose is the known, accepted
   state.
6. DONE (commitSB): a bazel-built console script opens with a 3-line sh preamble that re-runs it
   under the venv's own python. Residue: the arm skips under bazel; the preamble uses
   `readlink -f`; venv.bzl's `_relative_path` has no callers.
7. DONE 26d717d + 2cfbdf7: all of membudget, including retry-on-OOM and the ported .agda
   per-module path. substrate CONFIRMED that climbing only on a cgroup-counter-confirmed kill is an
   intended TIGHTENING: its bash 143 arm is a defect, since a SIGTERM would re-run a job someone
   meant to stop. It pins 2cfbdf7 and will run the one-module parity after its promote.
   AWAITING: that parity result. The original request, kept for the record:
   (a) MEMBUDGET_RETRY_OOM FIRST: a 137 re-enters at the next power-of-two bucket until the
       ceiling. The agda shim sets it on every compile.
   (b) PORT the `.agda` per-module path (not drop): auto sizes from THAT module's own peak
       history.
   A draft is landing in .claude/swarm/membudget-r3r5-proposed/. When it lands, send substrate the
   sha; it will swap with a one-module parity run. It will NOT swap mid-run: a sandbox promote is
   live under its membudget, and luthen is watching. substrate ACCEPTS 137 (not 143), exit 2 on a
   malformed AGDA_MB_*, and `run 0` as a zero cap.
8. transcriptstruct: STAGE 1 (records) DONE 43b2615; STAGE 2 (walk) DONE 9eeae60 (re-derived:
   w17/scan.py is lost); STAGE 3 (blocks) DONE 53560db; STAGE 4 (provenance) DONE 9549f93.
   STAGE 5 (query) DONE b523ca6; STAGE 6 (cli) DONE e571b02. THE PORT IS COMPLETE; substrate
   was told the key and sha (2026-09-24). TS1-c DECIDED, NO NEW DECODERS (measured with the new
   --raw mode, 2026-09-24):
   - queue-operation `enqueue` carries `content`, the queued message text, but that is a
     DUPLICATE: the cassian message queued at line 33 is delivered and already decoded at line
     41 as a user text block. Decoding it would double-count every queued message;
   - system is hook-run metadata (subtype stop_hook_summary, hookInfos, hookErrors);
   - file-history-* is file-backup bookkeeping.
   All stay unknown, now with a reason. AWAITING substrate: repoint Selftest.mk and
   tool_usage.py (tool_usage.py does NOT import it; the real consumers are 7 scratch tmi_* tools,
   substrate's W33), then delete scratch/transcriptstruct.py. Open: TS1-c NARROWED by
   Stats.unknown_types (ec95472; measured on TWO transcripts: ours at 84,188 records, and
   substrate's at 159,919 with unknown 53,239 across the same 11 types, summing exactly, with
   NO user/assistant/attachment type, so no decode bug, confirmed by substrate-9e; the
   content-bearing candidates are only queue-operation, system and file-history-*), tool_result:tool_reference (80 undecoded, real), TS1-d. Open decisions: TS1-c (decoders for
   system/summary records), TS1-d (invalid UTF-8: replace or report).
   STUDIED (.claude/swarm/transcriptstruct-study.md); the verdict is
   DECOMPOSE-AND-REPLACE. It has 119 ruff findings and 362 mypy errors, and is BLIND to 3 of the 7
   finding-swallowing shapes (0 of 15,113 attachment records decoded). The proposed
   mikemol-transcriptstruct is records → walk → blocks → provenance → query → cli.
   UNBLOCKED: the handover letter arrived (inbox/2026-09-23-substrate-transcriptstruct-handover.md).
   It confirms the sole copy and hands ownership to mtools; substrate deletes its copy after the key
   installs and its callers are re-pointed. FIXTURES ARE HELD pending substrate's operator (they
   would be private transcript excerpts in a GitHub repo), so the four blind-shape arms use
   SYNTHETIC records. The only automated caller is Selftest.mk; tool_usage.py is named but its
   import is unverified. NEXT after the pathsforward small bundle.
9. The census batch, which needs substrate's letters:
   - the corpus six go to mikemol-corpus;
   - witness_row and witness_family go to mikemol-witness;
   - ratchet_render goes to ratchet;
   - findings goes to mikemol-findings;
   - ratchet_log and ratchet_flags going to hooks is an OPERATOR call, because mdstruct would then
     depend on hooks.
10. DONE 778acf7. Residue: no_verify's own shlex split; one parser for all hooks.
    RULED YES (operator, 2026-09-24): no_chaining refuses a multi-line command as chaining, the
    way `;` is refused. A newline outside heredoc bodies, quotes and backslash continuations
    separates commands, and cmdparse.separate_lines (274ed7e) already knows where. no_chaining
    kept its own tokenizer and admitted multi-line commands, which was residue N1. NEXT after the
    pathsforward small bundle, BEFORE transcriptstruct, because it is small and already decided.
    Needs: a test that fails on HEAD, and a heredoc body (data) that must stay admitted.
11. DONE ec71fe7: mikemol-githook-pre-push packaged; githooks/ retired (521d77c was the spec).
    Substrate told the entry point and sha. SUBSTRATE SWITCHED (2026-09-24, pins at ec71fe7):
    a one-line stub exec, and an executable pre-push.local with the marker check. Controls: HEAD
    passes; a tip without the marker (9513286) is refused via the replayed stdin, exit 1.
    Deviation, accepted: its stub finds the venv from the hook's REALPATH, so el-openglo, still
    symlinking substrate's pre-push, keeps working until it switches. It then runs substrate's
    installed script with el-openglo's OWN pre-push.local, because the local hook comes from the
    pushing repo's toplevel. OPEN: el-openglo notice (no live session; substrate
    asked to relay); mtools self-install (post-commit auto-push interaction unmeasured);
    post-commit and prepare-commit-msg not ported.
    HISTORY: ⚑ INSTALL SHAPE OVERRIDDEN (substrate's operator, via substrate-9e 2026-09-24): "don't use
    symlinks. Import as packages." NEXT STEP: port githooks/pre-push to a CONSOLE SCRIPT
    `mikemol-githook-pre-push` in mikemol-hooks (Python). It captures stdin once, runs the
    in-flight check, then runs <toplevel>/.githooks/pre-push.local itself, with the same args and
    stdin. Each repo's .githooks/pre-push is then a one-line stub:
    `exec <venv>/bin/mikemol-githook-pre-push "$@"`. Port the 5 githooks_test arms to pytest (decoy
    repo in tmp_path). Then retire githooks/ and its symlink instruction, and send the entry-point
    name with the sha to substrate and el-openglo; el-openglo replaces its symlink into substrate
    the same way.
    ROLL-OUT, once the pre-push sha lands:
    (a) substrate: W34, its own pre-push.local carrying check 2, and a symlink to mtools' copy;
    (b) el-openglo: TELL them check 2 is no longer in the shared body. Their post-commit writes
        the marker, so they may want check 2 in their own pre-push.local;
    (c) mat230: DROPPED. It is RETIRED (substrate's operator, via substrate-9e 2026-09-24), so
        its vendor/ hard links need no switch. The roll-out set is substrate and el-openglo.
    SHARED GIT HOOKS PORT, with el-openglo's pre-push extension point (asked 2026-09-24,
    seconded by substrate). The shared pre-push captures stdin once, runs its checks, then runs an
    executable `<toplevel>/.githooks/pre-push.local` with the same stdin replayed; if it fails, the
    push fails. UNBLOCKED: the handover letter is at
    inbox/2026-09-23-substrate-githooks-handover.md.
    - Hooks handed over: pre-push, post-commit and prepare-commit-msg. pre-commit stays with
      substrate.
    - Links: el-openglo symlinks pre-push; mat230/vendor/substrate/.githooks/ hard-links all
      three (link count 2).
    - Substrate-specific: pre-push's post-commit-marker check. It moves to substrate's
      pre-push.local.
    - el-openglo's pushes may be blocked by that check today (unverified).
    Arms:
    - stdin is replayed byte-identically;
    - a failing local hook fails the push;
    - a non-executable local hook is ignored;
    - a missing local hook is ignored, with the shared checks still run.

SETTLED (operator, 2026-09-24): pathsforward D5, D6 and D7 get "don't care right now". The live
conservative defaults stand; do not ask again unless something breaks.
APPROVED (operator, 2026-09-24): ratchet_log and ratchet_flags go to mikemol-hooks, accepting that
mdstruct then depends on hooks. That happens when the census batch letters arrive.

ROW 2 LETTER ARRIVED: inbox/2026-09-24-substrate-corpus-batch-letter.md (mikemol-corpus; six
sole-copy, stdlib-only leaves; suites 16/24/7/6/10/13). IN PROGRESS, one module per tick:
RULING (substrate's operator, 2026-09-24): "We should not have things [like] corpus.ROOT." So:
NO module-level root constant in anything ported from substrate, however computed; the tree is
an explicit parameter with no default on every walker, and only a CLI entry point may resolve it
at call time, refusing when it can't. corpus DONE 4f1afc2 (the dist, plus the root fix); tree_root DONE f050acf (package_files names
its package and refuses a namespace one; the missing __init__.py is added); import_edges DONE
38082d0 (the suite beat the letter twice; substrate corrected §4); suite_discovery DONE 7e5e0e6
(it waited on 14ae21c, the long mypy timeout); promoted STAYS in substrate; suite_pragmas DONE
250ca18 (tenant names made the caller's). ROW 2 COMPLETE; substrate was sent the sha and the API
changes to repoint. NEXT: PYCHECK G1+G2 (linux-sources). Formerly listed next: promoted, suite_discovery, suite_pragmas. Tell
substrate the sha when all six land. ⚑ Design fix required, not a verbatim move: corpus.ROOT =
Path(__file__).parent.parent silently becomes site-packages when installed, so its 173 importers
would census the venv. The root becomes a parameter, or is resolved at call time and REFUSED
when it cannot be answered, with a red-on-HEAD fixture. The same check applies to
tree_root.package_files. SKIP_DIRS (substrate's agda/ and docs/) becomes caller policy.
Substrate's operator ruled the migration is substrate's path to green, so rows 3-6, N-d, N-e and
N-h are its top priority now.
ROW 3 COMPLETE 719587d (plus the N-d witness half); substrate was sent the sha and the API deltas.
NEXT: ROW 4 (ratchet_render → mikemol-ratchet).
HISTORY: witness_row DONE 2b108cf (the dist, plus the case-sensitive state arm);
witness_family DONE d947cb1 (18 arms); raw_bib DONE 72830da (N-d, whole); warrant_integrity DONE 9239e52
(path and parse required; the mutation grid added an unreadable-bib arm); NEXT warrant_bib, then
claim_of and tag, which finishes row 3. Remaining N-d witness half (raw_bib, warrant_integrity, warrant_bib with no
ROOT-derived constants, claim_of, tag).
ROW 3 LETTER ARRIVED: inbox/2026-09-24-substrate-witness-batch-letter.md (witness_row and
witness_family become a NEW mikemol-witness; sole copies, stdlib only, NO path handling;
suites 8/8 and 20/20; importers 26 and 36, all in substrate). ⚑ CONTRACT: the state spelling is
CASE-SENSITIVE (OPEN is uppercase, closed is not; is_open is state != CLOSED), so do not
normalise it. It is the base the N-d warrant split stands on. QUEUED after corpus's remaining
modules (promoted, suite_discovery, suite_pragmas).
ROW 4 LETTER ARRIVED: inbox/2026-09-24-substrate-ratchet-render-letter.md (ratchet_render
moves into the EXISTING mikemol-ratchet; sole copy, stdlib leaf, suite 29/29, 11 importers).
Two things do not travel as written:
- MINT_BYPASS tells the user to set SUBSTRATE_RATCHET_WRITE=1, but ratchet's core.py makes write
  a REQUIRED argument, so the text names a switch the package lacks; rewrite it to the real
  interface;
- list_pointer gives the --list hint only when argv[0] ends in .py, so an installed
  console-script gate silently loses it; the letter carries a red-on-HEAD fixture.
QUEUED after row 3.
PROMOTED DOES NOT MOVE (agreed with substrate-9e, 2026-09-24): ROOTS is substrate's roster, config
with no second user, so mikemol-corpus is FIVE modules, not six.
ROW 5 LETTER ARRIVED: inbox/2026-09-24-substrate-ratchet-log-flags-letter.md (ratchet_log, then
ratchet_flags, into mikemol-hooks; placement ALREADY APPROVED by the operator, "Sounds right";
sole copies, stdlib, suites 14/14 and 18/18). Two things do not travel as written:
- ratchet_log._DEFAULT_VLOGS_URL is a hard-coded address that once went stale and failed
  silently: make it a parameter or a by-name lookup, and report "not emitted" instead of falling
  back;
- store_argv/TENANT_FLAGS are substrate's --live/--sandbox policy: keep the generic "refuse an
  unstated choice between exclusive flags" mechanism, and substrate passes its pair.
Three scripts/hook_* twins import arg_after, so check whether mikemol-hooks already has one
before porting a second. CHECKED (2026-09-25): hooks has NO arg_after. shellcheck_cli
DELIBERATELY chose argparse over substrate's arg_after (its docstring). So for row 5, port the
generic mechanisms (unknown-flag refusal, and the refused unstated choice between exclusive flags)
and consider expressing them over argparse rather than reviving a hand-rolled argv reader; ask
substrate whether its three hook_* twins can move to argparse. QUEUED after row 4.
ROW 5a DESIGN (2026-09-25; source read at substrate/substrate/ratchet_log.py): the module becomes
mikemol.hooks.refusal_log. It records refused invocations, not ratchets, so the name says so.
- stream_tool, Refusal and _join travel whole (fixture: stream_tool(None) -> "unknown").
- log_fallthrough(tool, reason, typed="", refusal=None, *, destination: str | None). The
  destination is REQUIRED keyword with NO default: no hard-coded URL and no SUBSTRATE_VLOGS_URL.
  A caller resolves it by name (luthen's endpoints_query); None means "unresolvable".
- It RETURNS an Emission(emitted: bool, why: str) and still never raises. "no destination", "no
  curl" and "curl exit N" each report NOT emitted; the old version swallowed them, which is how
  :9428 died silently. Callers still compute their verdict first.
- redirected() / _url_override are DROPPED: with no module state there's nothing to redirect.
  The letter's "redirected restores" fixture is moot; residue, with that reason.
- Red on HEAD (the letter's §3.1): destination=None reports not emitted and curl is NEVER spawned
  (seam: module-level `which`/`run`, monkeypatched). Positive control: a destination plus a fake
  curl that exits 0 reports emitted, with the JSON line on stdin. Also: curl exit 7 reports not
  emitted with the code.
- S603 per-file entry in hooks/pyproject for refusal_log only.
5a LANDED fbe7063; substrate told.
ROW 5b DESIGN (2026-09-25; source read at substrate/substrate/ratchet_flags.py). It becomes
mikemol.hooks.flag_contract.
⚑ NOT OVER ARGPARSE, reversing this queue's earlier "consider argparse", with this reason: the
functions VALIDATE a raw argv that the caller then reads its own way (positional hook calls, bare
paths). Their callers are argv-membership gates, not parsers, and argparse would change every call
site to fix a typo problem. The source's own docstring measured this. shellcheck_cli choosing
argparse was a PARSER decision, which is a different job.
- `rest(argv)` travels whole: argv[0] is dropped only when it isn't a flag (the pre-sliced bug).
- `check_flags(argv, known, label, *, destination)`: refuses unknown flags, naming the known set,
  and emits "unknown-flag"; on accept it emits "accepted" (the adoption event). NO UNIVERSAL_FLAGS
  folded in: `--dry-run` is substrate's set_ratchet vocabulary, so the caller includes it in known.
- `Choice(flags: tuple[str, str], subject, consequence, reason, remedy="")`: the generic "refuse an
  unstated choice between two exclusive flags". `exactly_one(argv, label, choice, *, destination)`
  refuses neither (emitting its `reason`) and both, with its remedy line.
- `MUTATION = Choice(("--apply","--dry-run"), …, "unstated-mutation")` travels whole (ecosystem
  convention). TENANT is NOT here: substrate builds its own Choice with the tenant(require=…)
  remedy.
- DROPPED, with reasons: arg_after (hooks has none, and substrate's three hook_* twins are
  substrate's to move); SUBSTRATE_EXPLICIT_MUTATION=0 (a substrate-named ambient downgrade: a
  caller that wants advisory mode doesn't call the refusal, and an env switch arming a gate is the
  shape mtools declines); check_argv's mutates/needs_store booleans (a caller calls check_flags
  then exactly_one, in that order; the order rule moves into the docstring).
- Fixtures (the letter's §4): --queit refused naming --quiet; a known flag accepted; exactly_one
  refuses neither and both and accepts one, for MUTATION and for a caller-built pair; a pre-sliced
  argv still checks its first flag. Each emission goes to a fake curl, reusing refusal_log's test
  shape.
ROW 6 PORT ORDER (2026-09-25; import edges measured by grep over substrate/substrate/finding_*.py,
1365 lines total). Edges: bibkeys, mode, polarity -> kinds; entry -> kindspec (TYPE_CHECKING only);
keys_show -> keys; cli -> census, resolve. Nothing else. One commit per step:
 6.1 NEW dist mikemol-findings skeleton (clone witness/'s layout: pyproject, BUILD, rubric, bib,
     requirements, MODULE hub if needed) + finding_kinds (219 lines). §3.1: no ROOT; run(*argv,
     cwd: Path) with cwd REQUIRED; the three outcomes stay distinct and rc None never becomes a
     number.
 6.2-6.6 leaves: kindspec, restem, keys, census, resolve.
 6.7-6.9 on kinds: bibkeys, polarity, mode (§3.2: lens command via the Runner param; no
     `python3 scratch/toolmodes.py`).
 6.10 entry; 6.11 keys_show (NO suite: its fixture is written fresh); 6.12 cli.
Then tell substrate. The old-ledger swap is theirs.
⚑ 6.1 COLLISION (2026-09-25): the dist directory `findings/` ALREADY EXISTS. It is the repo's
tracked findings CORPUS (82 files: membudget, bazel, CENSUS-*). I scaffolded into it before
noticing (ruff format --check listed findings/bazel/mtools.md). No tracked file was touched. The
draft (pyproject, README, paper, locks, finding_kinds + 12 passing arms) was MOVED to
scratchpad/findings-dist/; its .venv must be re-synced wherever it lands. Directory name: asked
the operator. RULED: `ledger/` as mikemol-ledger (import mikemol.ledger.finding_*).
6.1 LANDED 09d0e2d; substrate told about the rename.
ROW 6 COMPLETE (2026-09-25): 6.1-6.12 landed, last at 45c8d35 (finding_cli). 12 modules, 89 arms.
Substrate was sent the swap signal with all 10 API changes; the old-ledger swap is theirs.
ROW 7 LANDED f9f0789 (spec_for + kind_of in mikemol.ratchet.keys); substrate told; key_spec retires
on their side. THE SUBSTRATE BATCH (rows 1-7) IS FULLY LANDED on mtools' side.
HOLD UNIT LABEL, bash side MEASURED (2026-09-25, substrate/scripts/membudget{,-ledger}): every bash
rewrite keeps a non-LEASE line. gc's `*)` arm copies it verbatim (ledger:119-120); release greps
out only `^LEASE <id>` (ledger:176); init/init --reset's _set_total awk `{print}`s every other line
(membudget:260); read_total reads only TOTAL_MB. So a `UNIT <word>` line survives both clients.
Bash's own status will still print "MB"; that is bash's cosmetic, and substrate's to take. NEXT
STEP: build it on the Python side: `init N --unit WORD` writes `UNIT WORD` (one word, refusing
whitespace, as labels do); status/hold/run print the unit; no UNIT line means MB; two UNIT lines
refuse, like two TOTAL_MB.
UNIT LABEL LANDED 7196dc1. ⚑ NOTICE PENDING for amr-skills (session unreachable at 2026-09-25T12:10;
deliver on next contact): the label is live under their `-e` install. Declare it with `init --reset 2
--unit contexts`, which keeps leases. `run` now REFUSES a non-MB ledger (exit 4, naming hold).
SUBSTRATE'S ORDER (2026-09-25, confirmed nothing is blocked on mtools): W40 ledger swap → W43
pycodemod letter → W41 pin bump (retires key_spec via f9f0789; picks up 09151ef and 859a10b) → W42
bash parity. W40's RUNNER IS COMPLETE: substrate.witness_run runs every kind, ours via
mikemol.ledger.finding_kinds, and it differences 7/7 against the origin on the live roster. Left
in W40: paper.toml verbs, the bib `check` rewrite, then deleting their finding_* family. W43 will
be a real letter, not notes (its shell-out census is still to run). W22's state they confirm next
tick.
FENCE ADMISSION HAS NO WAITER (summit ask `ask-membudget-hold-records-no-waiter`, filed by
amr-skills, 2026-09-25): ACCEPTED as a real defect. The ledger holds only TOTAL_MB and LEASE
lines, so arrival order cannot be represented, and a freed slot goes to whichever poll lands
first. linux-sources' commit gate starved behind three amr-skills walkers. Summit's witness
drives the real acquire() and reads OPEN: later arrival B is admitted ahead of waiting A. It
CLOSES on arrival-order admission (or a documented priority / bounded wait; tell summit if that
route is taken).
DESIGN SKETCH, not started:
- a `WAIT <ticket> <owner> <epoch> <mb> <label>` line appended under the lock at first block;
- admission grants only the oldest live waiter that fits (plus live-owner reaping of dead
  waiters, the same pid:starttime rule as leases);
- NOBLOCK/TIMEOUT remove the waiter line.
⚑ CROSS-CLIENT: bash gc must keep or understand WAIT lines. Its `*)` arm already keeps unknown
lines verbatim (measured for UNIT), but bash's own admission would ignore the queue, so FIFO
holds only when both clients honour it. That needs substrate's bash parity (their W42 lane).
Measure bash first, as with UNIT. Sequenced after the pycodemod core commit.
PYCODEMOD PORT PLAN (W43 letter landed: inbox/2026-09-25-substrate-pycodemod-port-letter.md):
- PLACEMENT: a NEW dist `pycodemod/` as mikemol-pycodemod (checked that the dir is free), with a
  CONSOLE SCRIPT `mikemol-pycodemod`. 7 ledger witnesses and summit's check shell out to it, and
  2 pre-commit gates (check_mypy_ratchet, gate_status) import it, so it has to be installable and
  importable from a hook's environment. Runtime deps: libcst (a REQUIRED dependency, which turns
  the cst-None blind spot into an import error) and climode (substrate/climode.py's shape, with
  scripts/ behaviour).
- DO NOT PORT the retired modes --attr and --importers. Port their clean successors instead,
  substrate/attr_reads.py and substrate/module_importers.py (pycodemod_retired_selftest 24/24),
  and keep the old spellings as refusing redirects so the routing tables keep working.
- DIFFERENTIAL BASELINE 407/408. The origin FAILS "a live hand-rolled memo classifies as a
  cache" (got None) and SKIPs the postgres case (UNMEASURED). Decide in the cleanroom whether the
  memo case is a defect to fix; either way it is NOT a port regression.
- The corpus root is an OPERAND (no ROOT, no scratch/jea/substrate defaults).
- OPERATOR-OWNED, NOT MINE: the settings.json allowlist entry for the new spelling, and the
  structural-query hook and struct-tools routing tables (a renamed mode keeps its old spelling or
  the table moves with it).
- SUBSTRATE THEN: repoint the 7 witnesses, then the 10 bare importers (gates first); hand the
  routing and settings to the operator; retire scratch/pycodemod.py with a refusing redirect once
  mtools' differential is green; re-register summit's check under the new owner.
- FIRST STEP: the dist skeleton + _pycodemod_core (637 lines; the leaf everything imports), with
  its selftest arms ported as pytest.
- CORE DESIGN (read at source, 2026-09-25):
  * ITS CORPUS WALK IS ALREADY PORTED. _roots/_resolve_root/py_files/PopulationError/
    _SKIP_DIRS/_GENERATED_DIRS are exactly mikemol.corpus (4f1afc2), with root required. So
    mikemol-pycodemod DEPENDS ON mikemol-corpus ("DEPEND never vendor"). This is the FIRST
    mtools-internal runtime dependency. Row 6 declined one only because ledger→bib reversed
    D3's direction, and this reverses nothing. NEW INFRA: a uv path source in the pyproject,
    `//corpus:corpus` in BUILD deps, and the dep hub. Pinned consumers get it via the one mtools
    sha anyway.
  * NO ROOT GLOBAL. The origin's `corpus` context manager does `global ROOT` so --archive/--in
    rebind the tree under every mode. The port's `corpus(path)` is a context manager YIELDING
    the tree Path (a temp dir for an archive, cleaned on exit), and every query takes `root`
    as a parameter. The global rebind is gone.
  * libcst REQUIRED (not try/except): the `if cst is None` guards and the "importable without
    libcst" contract go; the missing library is an ImportError at install time.
  * Moves nearly as-is: flagged_argv/operand_tail (the `--` convention), escapes,
    package_root, roundtrip, UNKNOWN/_value_of/_shape_of/_src_of, _per_file.
  * DISCARD_LEDGER is a path beside the scratch file: it becomes a parameter.
  * escapes' `errors="replace"` read: report an undecodable file as unread (the TS1-d rule),
    never decode it into a census.
PYCODEMOD SCOPING, READ-ONLY (2026-09-25, done ahead of W43 on the operator's nudge to take
initiative). The family is ~18.8k lines:
- driver scratch/pycodemod.py: 4,145 lines, 18 top-level defs, ~70 modes via _dispatch;
- 12 siblings scratch/_pycodemod_{core 637, query 3249, census 1821, sql 1661, fingerprint 898,
  split 783, control 695, exit 558, placement 481, ambient 427, commentary 331, selftest 3099};
- climode, in TWO copies (scripts/ 963, substrate/ 155 plus a 201 suite: resolve which the port
  depends on);
- libcst OPTIONAL (every CST mode returns [] when it is absent: an absence-lie to fix).
The 16 `# noqa` lines in the driver are all on imports (F401/E402), a re-export shim, dissolved
by the port.
DEFECTS FOUND IN literal_sites (_pycodemod_query.py:2817):
(a) linux-sources' f-string blindness, CONFIRMED AT SOURCE: it visits only cst.SimpleString; an
    f-string is cst.FormattedString with FormattedStringText parts, never visited. Its docstring
    promises role 'other' covers "an f-string part", so the doc claims what the code misses.
(b) SAME CLASS, NEW: `except Exception: continue` (lines 2874-2875) silently skips any file that
    fails to read or parse, which is ALSO a zero reading as absence. The cleanroom reports such a
    file as UNREAD. And `if cst is None: return []` is a third instance.
SUBSTRATE ANSWERED (2026-09-25):
- climode: pycodemod loads scripts/climode.py (963 lines) via sys.path.insert(ROOT/scripts) at
  pycodemod.py:939-940. substrate/climode.py is the clean promotion of it, differentially tested
  26/26. PORT AGAINST scripts/ BEHAVIOUR, TAKE substrate/'s SHAPE.
- (c) A FOURTH blind spot, measured by substrate: `--calls sys.path.insert scratch/pycodemod.py`
  reports 0 defs, 0 calls and 0 refs, while that exact call is at :939. Not bisected (the dotted
  target? the module-level position? both?). It becomes a cleanroom ARM next to the f-string pair:
  a dotted module-level call must be found.
  BISECTED BY mtools (2026-09-25), with a probe file holding the same calls at module level and in
  a function, run through substrate's own pycodemod:
    `--calls foo` (bare)             -> found :4 (module level) and :9 (function); correct
    `--calls insert` (last segment)  -> calls :3 and :8, PLUS refs :3 and :8
    `--calls sys.path.insert`        -> 0 / 0 / 0
  CAUSE: the DOTTED TARGET, not module-level position. --calls compares only a call's final
  attribute name, so a dotted query never matches and reads as a confident zero. TWO MORE
  defects surfaced:
    (d) every attribute call is counted TWICE, as a call AND a ref on the same line;
    (e) the last-segment query cannot tell sys.path.insert from any list's .insert.
  CLEANROOM ARMS:
  - a dotted query matches the full dotted callee, at module level and in a function;
  - one call is counted once;
  - `insert` alone reports its receivers, or is stated to be receiver-blind.
Cut plan (provisional): leaves first (core, then commentary, exit, placement, ambient), then query,
split into its modes, then census, sql, control, fingerprint; the driver last as a thin dispatcher;
selftest arms ported per module as pytest. Easily 15+ commits.
PYCODEMOD, NOT YET PORTED (linux-sources-fa, 2026-09-25; the operator routes tool defects to mtools):
there is NO pycodemod port in mtools; it is still substrate's scratch/pycodemod.py. Asked substrate
whether it is on their census. SUBSTRATE ANSWERED: NOT on their census; whether it ports is the
OPERATOR's call (surfaced to them by substrate). Under the operator's 2026-09-25 ruling a dirty
monolith is CLEANROOMED with a differential, never patched in place, so substrate won't touch
scratch/ meanwhile; it records the f-string blind spot so its own absence claims carry it. mtools
waits for a port letter. ⚑ OPERATOR RULED 2026-09-25: "Port it (cleanroom)". Substrate writes the
census/port letter (sole copy, importers, suite, what does not travel); mtools cleanrooms it into
clean modules with a DIFFERENTIAL against scratch/pycodemod.py, one commit per module as rows 1-7
were, and the f-string fix and linux-sources' test pair are in from the start. Placement (hooks
vs a new dist) is decided when the letter shows its importers. SUBSTRATE QUEUED THE LETTER AS W43;
it lands in inbox/ one or two ticks after their W40. ⚑ PLAN FOR: pycodemod is what the
structural-query hook and the struct-tools skill ROUTE textual queries to, so its shell-out census
is wide, and the ADOPTER list, not the importer list, will drive placement. It likely wants its own
console-script dist, as a tool every adopting repo installs, rather than a module inside
mikemol-hooks. LINUX-SOURCES' ACCEPTANCE PAIR, to be run against the entry point: 'stale_gate_build'
found (plain) and 'simultaneously' found (f-string), both in ls_gate/gen_gate_build.py. Then they
repoint their SKILL.md Python row. Tell them the entry point on landing. RECORD: linux-sources
RETIRED its substrate structural-query symlink; its routes check asserts the symlink is GONE and
arms only mtools' console script. PORT REQUIREMENT, measured by
linux-sources: `--literal` is BLIND
INSIDE F-STRINGS and returns a zero that reads as a real absence. In gen_gate_build.py:2606, "all
{…} generators are simultaneously clean" reads 0, while the control `--literal stale_gate_build`
reads 2 in the same file. Fix IN the port: walk the ast.Constant parts of a JoinedStr. Test pair:
a plain literal is found, and an f-string fragment is found.
Their second ask (the refusal pointer naming ../substrate/scratch/pycodemod.py) is THEIR data: the
hook reads routes and successors from the consumer's own .claude/skills/struct-tools/SKILL.md
(routing_table.SKILL_RELPATH), so they edit their table, and there is no mtools change.
PYCHECK SUPPRESSION GATE LANDED 859a10b (live-probed: `# ruff: ignore[print]` is refused with the
suppression block as its only finding); substrate told.
PYCHECK ADMITS NOQA (inbox/2026-09-25-substrate-pycheck-admits-noqa.md), ACCEPTED, with first-hand
evidence (this session the gate admitted my `# noqa: PLR2004` and `# type: ignore[call-arg]`).
DESIGN, next tick:
- hooks/src/mikemol/hooks/suppressions.py: `directives(source)` counts suppression COMMENT tokens
  via tokenize (noqa, type: ignore, ruff: noqa/ignore, pyright: ignore); strings never count.
- `added(before, after)` is the multiset difference, so moving a directive is not an addition.
- pycheck.analyze reads the pre-edit text from disk ("" for a new file) and folds a
  `--- suppression ---` outcome when anything is added, naming each directive and the per-file
  relief. Existing debt never blocks an unrelated edit.
- If `before` fails to tokenize, count 0 there (conservative). Arms: added noqa refused; added
  type: ignore refused; an existing one kept or moved is allowed; "noqa" in a string is allowed;
  the control (a clean edit) is allowed.
EL-OPENGLO NOTICE DELIVERED 2026-09-25 (el-openglo-11 live): console script, check 2 moved out, the
symlink still works, stub shape recommended. ACKED: they DID rely on the marker check. Next they
write pre-push.local (marker check plus their tree-writes gate, per their operator's 09-23 ruling),
then switch to the stub with mikemol-hooks sha-pinned; they check the marker by hand meanwhile.
The roll-out set (substrate, el-openglo) is covered.
TS1-d DECIDED AND LANDED 09151ef: invalid UTF-8 is reported per line as a MalformedLine, never
replaced; substrate and summit told.
RUN OWN-LEDGER PARENT LANDED 7ebad9b (operator: "Yes, same rule"). Substrate was sent both bash
parity asks (bash status unit, bash run on a non-MB ledger, bash run's cross-ledger parent).
NEXT CANDIDATES (after the unit label): run's
cross-ledger parent (ask first); the three open non-blockers (el-openglo notice, membudget parity,
W22 fixture pair, TS1-d).
6.7 bibkeys DECISION (2026-09-25): substrate's copy shells out to `python3 scratch/bibstruct.py
--entries` under ROOT (the §3.2 defect again, which the letter did not flag for bibkeys). I did NOT
switch it to mikemol-witness.raw_bib, though that is mtools' owning bib reader: it would be the
first mtools-internal runtime dependency, and ledger -> bib reverses the study's D3 ("bib ->
findings, never the reverse", restated in the letter's §5). Instead the entries lister is a
REQUIRED caller-supplied argv, run via finding_kinds.run with a REQUIRED cwd; the output contract
is "one key per line, first token", with the denominator and ⚑ rows skipped, unchanged. Substrate
passes its bibstruct argv. Revisit if D3 is ruled otherwise.
LESSON: check that a directory is free (`git ls-files <dir>`) BEFORE scaffolding a dist; and
never place a .py file with `cp`, because it skips the pycheck hook (use Write).
ROW 6 LETTER ARRIVED: inbox/2026-09-24-substrate-findings-letter.md (the finding_* cluster, 12
modules, into a NEW mikemol-findings; sole copies, closed in BOTH directions, so zero substrate
repoints; eleven suites pass; finding_keys_show has no suite, so its fixture is written fresh).
Two things do not travel as written:
- finding_kinds.ROOT is __file__-relative and is every witness run's cwd; installed, witnesses
  would read as UNRUNNABLE instead of wrong. cwd becomes a REQUIRED parameter (the no-ROOT
  ruling);
- finding_mode shells out to substrate's scratch/toolmodes.py under a bare python3: route it
  through the existing Runner Protocol as a parameter.
N-e ANSWERED: inbox/2026-09-24-substrate-key-spec-answer.md. key_spec is a STALE SUBSET TWIN of
the key schema (5 gates, where mikemol.ratchet.keys has 7), so ROW 7 CLOSES AS RETIRE: add
spec_for (gate module filename -> schema; None when undeclared, never a default) and kind_of (the
trailing kind field) to mikemol.ratchet.keys; substrate then repoints 5 consumers and deletes
key_spec.
N-h RE-MEASURED (substrate-9e, 2026-09-24, a new reader `python -m substrate.package_graph <pkg>`):
- modules 430 against the study's 415; the +15 are this session's additions;
- edges 583 distinct = 564 eager + 19 deferred-only;
- the eager 564 EQUALS the study's 564 despite added edges, which is a coincidence of COUNTS, not
  proof of the same SET (the sets were not diffed);
- in-degree corpus 108 / witness_row 11 / warrant_bib 11 match the study;
- NOT re-measured: 131 components and 43 non-singleton at the hub cut (the reader lacks
  components). Not needed for the current batches, so not asked for.
N-d ARRIVED: inbox/2026-09-24-substrate-warrant-split-letter.md. EVERY §4 item is now answered.
It stands on row 3 (witness). The split:
- raw_bib and warrant_integrity go to witness whole;
- warrant_bib goes to witness once its PROJECT/BIB/CONFIG constants go (they derive from
  corpus.ROOT, the no-ROOT ruling); consumer_fields takes config as REQUIRED;
- warrant_records splits at one call: records() (the sole paperkit.bib.parse contact) goes to
  PAPERKIT with path made required; claim_of and tag are pure and go to witness;
- engine_grades and engine_edges are wholly paperkit-facing (engine_edges has no suite).
⚑ THE PAPERKIT HALF IS NOT mtools' TO LAND: paperkit is another repo with its own session
(paperkit-b4). mtools ports the witness half; the paperkit half is a letter FROM substrate TO
paperkit, and it must pass the paperkit-use census's freeze state, which is now CALLED at 3d030b5.
Tell substrate before starting row 3.
DONE b8b3e41 (2026-09-25); amr-skills told. IN PRODUCTION: 6 walkers, 2 holding, 4 queued.
FOLLOW-UP (amr-skills): status and admission print "MB" for a ledger counting contexts. Proposed:
`init N --unit contexts` writes a `UNIT contexts` line, which rides as a non-LEASE extra (both
clients keep extras through their rewrites; check bash's side before relying on it). status and
hold then print the unit; with no UNIT line, MB as today. Also: I gave the wrong path. fence/.venv
has NO console script; the working install is `uv pip install -e ~/github/mtools/fence`.
Doc lesson: after wiring hold, check the ledger count against an independent read (nvidia-smi).
Consumers that never lease are invisible to it; seen in practice during their cutover. OPEN residue: `run` still nests under an inherited
parent from ANOTHER ledger. Not measured whether that matters for `run`; ask before changing it.
FENCE `hold` VERB (filed by amr-skills-48, 2026-09-24): `mikemol-membudget hold <MB> <LABEL> -- <cmd>`.
Records a lease without capping the command, for a resource the fence can't enforce (first use: GPU VRAM).
It shares `run`'s admission, waiting, NOBLOCK/TIMEOUT and exit codes. It has NO fence, NO climb,
and must NEVER cap the command: a separate verb, not a flag on `run`. Its output states
"ACCOUNTING ONLY. Nothing enforces this number." Ruled: no verifier hook in the tool; a consumer
that can measure (nvidia-smi) checks on its own side. Waiting: amr-skills and linux-sources.
Priority: after row 4 lands, ahead of rows 5-7 (two parties blocked).
UNIT-AGNOSTIC (amr-skills, 2026-09-24): their logs show CUDA_ERROR_ALREADY_ACQUIRED (a context
acquisition failure) 123 times, so VRAM MiB may be the WRONG quantity. Docs, help and tests speak
of "units of an agreed resource", never VRAM-specific; no VRAM worked example.
My EXCLUSIVE_PROCESS lead is REFUTED: Compute Mode DEFAULT and no MPS (measured by linux-sources).
REQUIRED ARM: a walker holding on TWO ledgers (contexts + MiB), nested. The inner hold must NOT
take a parent lease from a DIFFERENT ledger, so cascade-gc never crosses ledgers. Test with two
MEMBUDGET_FILEs, not two holds on one.
MEASURED (linux-sources, 30 probes per shape): the constraint is CONTEXT COUNT, not VRAM. 3 foreign
contexts with ~2.7 GiB free fails 0/30; 1 context with ~2.5 GiB free passes 30/30. First consumer:
a contexts ledger with TOTAL ~2 (threshold is somewhere in 2-3, not pinned). Their interim VRAM-
threshold cap RACED (6 walkers started, 3 got through), so `hold`'s atomic admission is the actual need.
FULL TABLE: 2 contexts 30/30 OK; 3 fail 0/30 whether torch (C) or cupy (G), so the library is
ruled out as a cause; the cutoff is crisp. OPEN: whether the limit also counts desktop compute
apps (kwin, VS Code). If so, TOTAL varies. `init --reset` can resize under live leases, but a
moving TOTAL is the consumer's problem; `hold` stays static. amr-skills has capped itself at 2
walkers until `hold` lands.
BLOCKED 2026-09-24: the pycheck format bar refuses edits to fence/tests/test_membudget_cli.py.
mtools was NEVER formatted: 104 files, all 8 dists plus 3 root files (`ruff format --check`).
The bulk `ruff format` was DENIED by the auto-mode classifier; asked the operator.
PYCHECK FORMAT-BAR OPT-OUT (substrate-9e, 2026-09-25): f328d38's format bar refuses every edit
to substrate's never-formatted files. MEASURED on a probe: `[tool.ruff.format] exclude` does
NOT reach the stdin format check; `[tool.ruff] extend-exclude` does, but drops lint too. So NO
format-only knob exists. Offered: (1) a bulk ruff format pass by substrate, or (2) a new
`[tool.mikemol-hooks.pycheck] format-exclude = [globs]`, skipping only ruff-format for matching
paths and stating the skip. RESOLVED: substrate's operator chose (1) and bulk-formatted 1046 files.
RESIDUE, do NOT build (2): substrate-9e relayed its operator's ruling that the format requirement
is the operator's own rule for ALL their repos, so an opt-out would be a sanctioned way around it.
An adopting repo does a bulk format pass instead. (Relayed by a peer, not typed here; it only
narrows scope, so I acted on it.)
PYCHECK G1+G2 DONE f328d38; linux-sources told to re-pin and re-run its parity script.
HISTORY: ⚑ PYCHECK PARITY GAPS (linux-sources-fa, 2026-09-24; they BLOCK linux-sources' migration off its
local hook fork, its W33). Measured: same armed Write payloads to both hooks, 6/8 cases match,
script at ~/.cache/linux-sources-drafts/w33/parity.py. Both ACCEPTED:
- G1, NO FORMAT BAR: a ruff-check-clean, mypy-clean but ruff-FORMAT-dirty file is ALLOWED; add
  `ruff format --check` beside `ruff check`, or the edit gate admits what the commit gate refuses;
- G2, CREATING A PACKAGE MARKER IS REFUSED: writing a new `<dir>/__init__.py` into a markerless
  dir is denied with INP001 for the very file that supplies the marker (pre-write, ruff reads the
  filesystem). Fix: add `--extend-ignore INP001` for a file named exactly `__init__.py`, on ruff
  check only; a module in a markerless dir must still be denied, and an existing package's
  __init__ must still pass.
Each needs a red-on-HEAD arm from the payloads. Done BEFORE row 3; tell linux-sources-fa the sha.
SEQUENCE: corpus (suite_discovery, suite_pragmas) → PYCHECK G1+G2 → row 3 witness plus the N-d witness half →
row 4 ratchet_render → row 5 ratchet_log/flags → row 6 findings → row 7 retire (spec_for/kind_of).
⚑ GATE BLOCKED BY HOST LOAD (2026-09-24 ~20:40): loadavg 36-45 on 24 CPUs. A cold host mypy on
corpus: wall=295.12s, user=2.93s, sys=0.19s, so 99% of the wall time is waiting, not work. Every
cold sandboxed mypy target exceeds its 60s `small` limit. suite_discovery is READY but
unstaged; retry when load falls.
SATISFIED: N-f (transcriptstruct: handed over and replaced, e571b02 + ec95472). N-c is DONE on
substrate's side (below). It unblocks T3, the gate/hook layer, which still needs its own N-a
letter.
N-c ARRIVED (substrate-9e, 2026-09-24, UNCOMMITTED in substrate's working tree, so copy from
there): the roster (Gate, hook_gates, and the boundary readers authority, call_rows, field,
entry, advisory_gates) moved verbatim into a new leaf, substrate/hook_roster.py, importing only
gate_module. commit_refusal re-exports it via __all__; sync_verdict reads hook_roster and no
longer imports commit_refusal, so the cycle is cut. Suites: commit_refusal 33/33, sync_verdict
41/41, wired_mode 18/18. Context: .claude/swarm/census-reply.md §4 N-c.

RULED (substrate's operator, via substrate-de 2026-09-24), N-g / C13: "As a rule, depend on
mtools' package; it reduces the code load in this repo." It is a STANDING rule: every future
depend-or-vendor question for substrate is DEPEND. The T1 core layer can move in any order mtools
chooses.

PYCODEMOD QUERY SPLIT PLAN (surveyed 2026-09-25, W24 step 3; read from substrate
scratch/_pycodemod_query.py at 3,250 lines, which is a SNAPSHOT that can drift):
- Leaves done: commentary 48b4cfb, exit 3b712f7, ambient ac4f358. `placement` is NOT a leaf: it
  imports KwIndex and scan.
- query is NOT dependency-clean either. It imports `_code_lines`, `aliases` and the def-cache
  trio (_DERIVER/_PARSE_CACHE/_SCHEMA/_ignore_cache) from `_pycodemod_census`. So `shape_sites`,
  `alias_hint` and `_cached_defs` wait until those census pieces land. Everything else in query
  depends only on core.
- Q1 `mikemol.pycodemod.sites` — the `_Scan` visitor, `scan` and `KwIndex` as ONE module. It is
  the seam four-plus modes and placement consume. Redesign:
  * scan RETURNS a `Sites` value (rows, per-call facts, population, skipped, target). That value
    IS the context stamp, so the KwIndex out-parameter and its `.check()` dissolve rather than
    port. `scan.skipped` / `scan.population` as function attributes go.
  * Per-call facts become one frozen `CallFacts` (keywords, shapes, constants, context,
    positions, possrc, receiver, conds) instead of eight parallel dicts.
  * Origin defects to fix, each needing a red arm (or a stated missing-name red):
    (a) facts are keyed by (path, LINE), so two calls on one line overwrite each other. Key by
        (line, column).
    (b) An attribute call `x.f()` is counted as a call AND a ref: visit_Name sees `f` in
        Attribute.attr, and only a bare Name func is excluded. This is the known double-count.
    (c) visit_If pushes the test for the whole If, so the else/elif body reads as guarded BY the
        test. Use libcst's visit_If_body/leave_If_body hooks so only the body carries it.
    (d) The context stack follows only FunctionDef. A method's context is its bare name; qualify
        it with the class.
    (e) `except Exception` around parse and visit hides visitor bugs (the origin's own
        documented incident). Catch ParserSyntaxError only; a visitor bug must RAISE.
    (f) A dotted target reads 0: the bisected defect, still owed its cause. Re-measure against
        the new module with a red arm first.
        RE-MEASURED 2026-09-25 against the origin's scan() (scratch probe; fixture below). The
        ZERO DOES NOT REPRODUCE at scan(): `store.connect` returns rows. It OVER-reports instead.
        On `sqlite3.connect(1); store.connect(b=2)` it returns TWO store.connect rows, because
        recv[5] is overwritten by the second call ((a)). `x.store.connect()` matches as well,
        because only the last segment is kept ((g)). So the earlier zero lives in the CLI or
        driver layer: re-check it when the driver is ported, not in sites. The same probe
        CONFIRMED (b) (every attribute call is also a `ref`), (c) (an else-body call carries
        conds ['c']) and (a) (line 5's keywords are {'b'}; sqlite3.connect's entry is lost).
        Fixture: `import store / store.connect(a=1) / def f(): x.store.connect() /
        sqlite3.connect(1); store.connect(b=2) / if c: pass / else: store.connect()`.
    (g) Receiver-blindness: the receiver is the last attribute segment only. Record the full
        dotted text and state it as spelling, not resolution.
  * DROP the process-global LRU _WRAPPER_CACHE (env-sized). The core stays pure; a cache is the
    driver's decision, keyed on (path, mtime_ns, size) if it is ever wanted.
- Q2 then the ONE-OPERAND modes over `sites`, grouped by question: calls/dead/forwards/
  asserted/values (keyword readings); attr_reads/module_importers (retired --attr/--importers
  redirect here); swallows/_feeds_verdict; callgraph/reaches/verdict_returners;
  reifies/resorts/funcnames; literal_sites/key_reads/source_of/bindings; rivals/collisions.
- Q3 placement, over `sites`.
- DEFERRED, NOT DROPPED (2026-09-25, Q2f): `funcnames` / `_generic_func_names`. The mode grades
  SQLAlchemy `func.<name>` calls as `generic` (translated per dialect) or `verbatim` (passed
  through), and its authority is SQLAlchemy's PRIVATE `sqlalchemy.sql.functions._registry`. Porting
  it makes SQLAlchemy a runtime dependency of a general Python codemod tool, whose only required
  dependency is libcst. That is a dependency-surface decision, not a port step. Options: an optional
  extra (`mikemol-pycodemod[sqlalchemy]`) that refuses loudly when absent; a separate small dist;
  or leave it in substrate.
  RULED (operator, 2026-09-25, via AskUserQuestion): OPTIONAL EXTRA. Ship `funcnames` inside
  mikemol-pycodemod behind `[project.optional-dependencies] sqlalchemy = ["sqlalchemy"]`. Without
  SQLAlchemy the mode REFUSES loudly (an ImportError-shaped refusal naming the extra); it never
  grades every call `verbatim`. An empty or moved `_registry` also refuses, as in the origin.
  Needs: a pycodemod_dev hub lock that includes the extra so the tests run under bazel, and a
  red arm for the absent-extra refusal. Port it after Q2g.
- The census pieces query needs (_code_lines, aliases, the def cache) come with the census
  split, after Q2.
- Q2 DONE: funcnames ca312cb (optional extra), rivals/collisions 7acbe8b. Q3 DONE: placement
  6bc536f + disagreement 86befee.

PYCODEMOD CENSUS CUT PLAN (surveyed 2026-09-25 from substrate scratch/_pycodemod_census.py,
1,821 lines; a snapshot that can drift). The module is TWO things. One is general Python
queries. The other is substrate's own instruments, coupled to its Agda build, paperkit, its
witness registry and a mypy run with cwd=ROOT (22 ROOT/agda/paperkit/jea references).
PORT, one commit each, in this order (every repo constant becomes an OPERAND):
- C1 `_code_lines` (the code-vs-comment/docstring line set) + `module_size` / `module_size_all`.
  OVERLARGE_LINES and INCIDENT_HALVINGS are substrate data (INCIDENT_HALVINGS names
  jea/metalanguage/schema.py), so the threshold and the incident map are arguments.
- C2 `aliases` + `_sibling_modules`: the import-form census (BARE / AS-MOD / FROM / FROM-AS).
  Then query's `alias_hint` and `shape_sites`, which waited on `_code_lines` and `aliases`.
- C3 `imports`: what the corpus imports, graded against declared deps. `_declared_deps` reads
  ROOT/pyproject.toml, so the declared set (or the pyproject path) is an operand.
- C4 `crossings`: containers crossing a function boundary. Its _CORPUS name set is
  substrate-flavoured (agda_files); read it before deciding whether it is an operand.
- C5 `module_state`: module-scoped mutable state and its mutators.
- C6 `writes_by_default` and `discriminates` (does a module's `_selftest` discriminate under
  mutation). Read both first: `discriminates` may be a repo convention (`_selftest`), not a
  Python fact.
DO NOT PORT (substrate's own instruments; tell substrate by letter, B1):
- `type_errors`: runs mypy with cwd=ROOT, ratchet-keyed. mtools has mikemol-ratchet and the
  pycheck hook for this; a second mypy census would be a rival body.
- `build_artifact_readers` / `_artifact_readers`: the Agda build vocabulary
  (FAILURE_BEARING, SUCCESS_ONLY).
- `touches`: defaults to catalog/library/items.py, substrate's witness registry.
- `paperkit_projects`: a paperkit fact; the owner is paperkit (ask summit whether it already
  offers it before anyone ports it).
- The def cache trio (_PARSE_CACHE, _SCHEMA, _DERIVER, _ignore_cache) and `_l2_cached` /
  `_corpus_key`: caches belong to the driver (rivals 7acbe8b already dropped the def cache).
- `importers`: the retired spelling; `imports.importers` (8a0786a) is the successor.
- The `_print_*` printers and ROUTE: the driver's.
THEN sql (1,661 lines), control (695), fingerprint (898): survey each the same way first.
C6 DECIDED (2026-09-26, read at source):
- `discriminates` IS DO-NOT-PORT. It drives a module's `_selftest()` (bool return, printed FAIL
  lines) with mutator regexes that name substrate's own code (`rows is None or "__unrunnable__"`,
  `ratchet.set_ratchet`, `POPULATION =`, `con.execute(q, args)`), and writes mutant files beside
  the source. That is substrate's convention and substrate's defect list. mtools' mutation grid
  (//<dist>:mutants, body->raise) is the general instrument; a second one would be a rival body.
  Add it to the DO-NOT-PORT letter.
- `writes_by_default` IS PORTED, on the AST, because its line regexes measurably fail
  (origin probe under the venv): `open(os.path.join("x", "y"), "w")` -> "no write call";
  `Path("out.txt").write_text(...)` -> "no write call"; a docstring mentioning "--apply" gated a
  file that writes unconditionally. The fixture-function name (`_selftest`) and the gate flag
  (`--apply`) are substrate conventions, so they become operands.
  DONE: C1 size 04b4eca, C2 aliases 215917b (+ hints 65dc5e5, shapes 7bd9301), C3 deps 30d6a25,
  C4 crossings 158660e, C5 modstate 1c4f500, C6 writes de104f6.

PYCODEMOD SQL / CONTROL / FINGERPRINT SURVEY (2026-09-26, read at source; snapshots that can drift).
All three are substrate's own programs, not general Python queries:
- `_pycodemod_control.py` (695) — DO-NOT-PORT. It measures how much Python control flow is left to
  move into substrate's SQL engine ("ladder logic", its own docstring). Its kinds (row-iteration,
  row-branch) are defined by substrate's store-reader predicates, imported from `_pycodemod_sql`,
  and its epsilon boundary is that program's. A general control-flow roster would be a new
  design, not a port; nobody outside substrate has asked for one.
- `_pycodemod_fingerprint.py` (898) — DO-NOT-PORT. It is built on control's `_Census`, seeds from
  substrate files (`jea/metalanguage/schema_decl.py`, `query_decl.py`), and its prime-fingerprint
  algebra is LIFTED from gabion (`gabion/src/gabion/analysis/core/type_fingerprints.py`). Porting
  it would make a THIRD copy of gabion's algebra (census-kit B4: record, never quotient). If the
  algebra is wanted as a shared leaf, its owner is gabion; ask there first.
- `_pycodemod_sql.py` (1,661) — MOSTLY DO-NOT-PORT, one piece DEFERRED:
  * DO-NOT-PORT: `portable_sites` and the `_pg_*` probe connections (live postgres against
    substrate's tenants); `rawread_sites`, `snapshot_sites`, `relalg_sites` and the
    `is_store_read` / `store_reader_fns` family (keyed on substrate's STORE_CONNS /
    STORE_READERS names); `sql_sites`' style grading (substrate's query_defs / query_sql /
    query_builders split); `_core_func_sites` (funcnames covers the general SQLAlchemy question,
    ca312cb).
  * DEFERRED, NOT DECLINED: the pure SQL-string relation reader (`sql_rel_roles`, `sql_relnames`,
    `sql_kind`, `sql_rw`, and `relname_sites` over literals). It is general, but its only
    consumer is substrate. Under the operator's membership ruling (a component earns a place by
    reuse ACROSS repos) it is ported when a second repo asks, not before.
PYCODEMOD DRIVER MODE MAP, DRAFT (2026-09-26, from substrate scratch/pycodemod.py MODES, 63 flags).
PORTED LIBRARY -> CLI mode (the printer is the driver's, the function exists):
  --calls, --guarded -> sites.scan (+ hints.alias_hint as the blind-spot footer)
  --placement -> placement.placement ; --unbound-snapshot -> placement.disagreement
  --ambient -> ambient ; --swallows -> swallows ; --exits -> exit ; --reaches -> graph
  --forwards, --asserted, --values -> arguments ; --dead -> dead
  --literal -> strings.literal_sites ; --key -> strings.key_reads
  --binding -> definitions.bindings ; --source -> definitions.source_of
  --aliases -> aliases ; --collisions, --rivals -> rivals ; --funcnames -> funcnames [extra]
  --reifies, --resorts -> ordering ; --size -> size ; --imports -> deps.import_census
  --crossings -> crossings ; --state -> modstate ; --shape -> shapes
  --commentary (and likely --blocks, --lines, --kinds) -> commentary : CONFIRM on read
RETIRED SPELLINGS -> refusing redirects that name the successor:
  --attr -> attr_reads (imports.attr_reads) ; --importers -> module importers (imports.importers)
DO-NOT-PORT -> refusing redirect that names where it lives (substrate's scratch/pycodemod.py):
  --types, --artifacts, --touches, --projects, --discriminates, --control, --fingerprint,
  --portable, --rawreads, --relalg, --snapshots, --sql, --collision-apex (jea templatize)
DEFERRED (second consumer): --relname (SQL relation reader)
RESOLVED 2026-09-26 (each read at its Mode(why=...) and function):
  ALREADY PORTED (core, de84d07): --escapes -> core.escapes ; --package -> core.package_root ;
    --roundtrip -> core.roundtrip.
  COMMENTARY (ported): --commentary -> commentary_census ; --lines = its rows ;
    --kinds -> commentary_kinds ; --blocks -> commentary_blocks.
  TO WRITE (general, small): --discards (return value used vs discarded, per call; over
    sites.scan call rows) ; --layout (top-level statement groups with first/last line and
    code lines, over size.code_lines) ; --fix-owes-callers (join sites.scan call rows with
    `git diff --name-only REV`; its tests use a DECOY repo, never the real one).
  DRIVER CONCERNS, not modes to port: --sites (a per-site detail option other modes take) ;
    --diagnose (every mode already returns `skipped` with the parse error; the driver prints
    it) ; --declare-modes, --banner, --check-contracts, --available (the origin describing its
    own mode table; the new driver's table is the argparse parser plus one declared MODES map,
    and --available has no meaning when libcst is a required dependency).
  DO-NOT-PORT: --sqlname (substrate's `q_<name>` named-query convention) ; --last (replays a
    PERSISTED census; this port persists nothing).
  DEFERRED: --split (a file-splitting codemod WRITER behind --apply; this dist's declared
    purpose is queries; it is ported when a second repo asks, and stays in substrate).
  NOT A MODE: --selftest; its 408 cases ARE the differential baseline.
CONSEQUENCE: the library layer of the port is COMPLETE. What remains is the DRIVER: the CLI mode
index over the ported modules, the retired spellings (--attr, --importers) as refusing redirects,
[project.scripts] mikemol-pycodemod, then the differential against substrate's 407/408. The
DO-NOT-PORT letter to substrate now also lists control, fingerprint and the sql pieces above.

W34 SLICE 2 LANDED (2026-09-27): `attr-reads` (imports.attr_reads) and `importers`
(imports.importers) are wired into cli.MODES; both retired their RETIRED entries (cli.RETIRED is
now empty — nothing else has been retired yet). 4 new tests in test_cli.py, 4 warrants
(pycodemod-cli-*), rubric's cli heading updated from "Three Modes" to "Five Modes". 320
pytest/ruff/mypy clean on the host venv. NEXT for W34: re-read the DRIVER MODE MAP for any other
already-ported library module not yet in cli.MODES (the map lists many one-to-one mode->function
pairs still unwired: sites.scan's --guarded footer, placement.placement/disagreement, ambient,
swallows, exit, graph, arguments' three flags, strings' two, definitions' two, aliases, rivals,
funcnames, ordering, size, deps, crossings, modstate, shapes, commentary's four spellings, plus the
TO WRITE small modes: discards, layout, owes' fix-owes-callers-successor naming clash to check).

W34 SLICE 3 LANDED (2026-09-27): `swallows` (swallows.swallows) and `exits` (exit.exits) wired
into cli.MODES, following the exact attr-reads/importers pattern (TYPE_CHECKING-only dataclass
imports for `Swallow`/`ExitRow`, printer helpers, handler functions over `report.incomplete`, new
subparsers taking only `paths`). 4 new tests in test_cli.py, 4 warrants (pycodemod-cli-swallows-*,
pycodemod-cli-exits-*), rubric's cli heading updated from "Five Modes" to "Seven Modes". 324
pytest/ruff/mypy clean on the host venv. NEXT for W34: ambient (needs a `--root: Path` flag design,
deferred from this slice as more complex than paths-only), graph's callgraph/reaches (need a
`Sites` object from sites.scan plus extra params, deferred), plus still-unwired: placement,
arguments' three flags, strings' two, definitions' two, aliases, rivals, funcnames, ordering, size,
deps, crossings, modstate, shapes, commentary's four spellings, discards, layout, owes'
fix-owes-callers-successor naming clash to check.

W34 SLICE 4 LANDED (2026-09-27): `verdicts` (graph.verdict_returners) wired into cli.MODES --
simple paths-only shape like swallows/exits. graph's other two functions (callgraph, reaches)
stay deferred: callgraph needs a Sites object from sites.scan, reaches needs a graph+start+targets
triple, both more plumbing than a paths-only mode. 2 new tests, 2 warrants (pycodemod-cli-verdicts-*),
rubric's cli heading updated from "Seven Modes" to "Eight Modes". 326 pytest/ruff/mypy clean on the
host venv. NEXT for W34: ambient still needs a --root flag design; still unwired: placement,
arguments' three flags, strings' two, definitions' two, aliases, rivals, funcnames, ordering, size,
deps, crossings, modstate, shapes, commentary's four spellings, discards, layout, owes'
fix-owes-callers-successor naming clash to check.

W34 SLICE 5 LANDED (2026-09-27): `disagreement` (placement.disagreement) wired into cli.MODES,
paths-only. The unparseable-file test first failed: sites.scan's documented needle prefilter
("a file whose text does not contain the bare name is excluded soundly ... and is not a skip")
excludes a bare `def (:` before parsing, so the fixture carries `require_at_entry` to reach the
parse — the same fixture correction attr-reads needed. NOT a sites.py defect. Carried residue:
placement.writes_store and binds_snapshot_at_entry track NO skips at all, so disagreement's
skipped set covers only the two placement() passes; a file unparseable that holds only a
store-write needle (e.g. `upsert`) and no entry/snapshot needle is invisible to the banner.
Unmeasured whether that is reachable in practice. 2 new tests, 2 warrants, rubric "Eight Modes"
to "Nine Modes". 328 pytest pass, ruff/mypy clean. NEXT for W34: placement() itself (forms
args), ambient (--root), callgraph/reaches, and the rest listed above.

W34 SLICE 6 LANDED (2026-09-27): `placement` (placement.placement) wired into cli.MODES over its
DEFAULT forms (ENTRY_FORMS, FIRST_WRITE_FORMS) only. Declined for this slice: a `--form` flag to
override them -- no caller has asked, and origin's spelling for it is unverified here. The
unparseable fixture carries `require_at_entry` (scan's needle prefilter, per slice 5). 2 tests,
2 warrants, rubric "Nine Modes" to "Ten Modes". 330 pytest pass, ruff/format/mypy clean. NEXT
for W34: ambient (--root), callgraph/reaches, arguments' three flags, strings' two, definitions'
two, aliases, rivals, funcnames, ordering, size, deps, crossings, modstate, shapes, commentary's
four spellings, discards, layout, owes' successor naming clash.

W34 SLICE 7 LANDED (2026-09-27): `modstate` (modstate.module_state) wired, paths-only; no needle
prefilter in modstate, so the bare `def (:` fixture reaches the parse. 2 tests, 2 warrants, rubric
"Ten Modes" to "Eleven Modes". 332 pytest pass, ruff/format/mypy clean. Remaining paths-only
library entry points (measured by grepping `def <name>(paths: Sequence[str])`): layout.layout,
rivals.collisions, ordering.reifies, core.escapes, exit.catchers, exit.interlock. NEXT for W34:
those, then ambient (--root), callgraph/reaches, and the flag-taking modes.

W34 ATOMIZED (2026-09-27, operator): the remaining modes are now one waypoint each, W52-W85, under
W34 as a blocked umbrella; see .claude/paths-forward.md. Per-mode notes continue below by symbol.

W52 LANDED (2026-09-27): `layout` (layout.layout) wired, paths-only, no needle prefilter. 2 tests,
2 warrants, rubric "Eleven Modes" to "Twelve Modes". 334 pytest pass, ruff/format/mypy clean.

W53 LANDED (2026-09-27): `collisions` (rivals.collisions) wired, paths-only. Adding it tripped
ruff PLR0914 (16 locals > 15) in _build_parser, so every paths-only subparser now comes from one
_PATHS_ONLY (name, help) table -- the remaining paths-only waypoints (W54-W57) add a table row, not
a local. 2 tests, 2 warrants, rubric "Twelve" to "Thirteen Modes". 336 pytest pass, clean.

W54 LANDED (2026-09-27): `reifies` (ordering.reifies) wired, paths-only, one _PATHS_ONLY row.
2 tests, 2 warrants, rubric "Thirteen" to "Fourteen Modes". 338 pytest pass, clean. Noticed, not
fixed: ordering.py's module docstring says `funcnames` is NOT PORTED, but funcnames.py exists and
W65 wires it -- a stale sentence for whoever lands W65 to correct.

W55 LANDED (2026-09-27): `escapes` (core.escapes) wired, paths-only. core.Escapes has a different
shape (found + unread: list[str], NO per-file reason), so the handler passes one merged reason,
"unread (unreadable, undecodable or uncompilable)", to report.incomplete rather than invent a finer
one. Residue: core.escapes should carry a Skip per file like every other census; minted as its own
waypoint. Also measured: report.incomplete exits 1 only when EVERY file was skipped (read == 0), not
when any was -- a mixed population with skips exits 0 with the banner. 2 tests, 2 warrants, rubric
"Fourteen" to "Fifteen Modes". 340 pytest pass, clean.

W56 LANDED (2026-09-27): `catchers` (exit.catchers) wired, paths-only, one _PATHS_ONLY row. 2
tests, 2 warrants, rubric "Fifteen" to "Sixteen Modes". 342 pytest pass, clean.

W57 LANDED (2026-09-27): `interlock` (exit.interlock) wired, paths-only, one _PATHS_ONLY row; row is
`interlock <callee> <defname|-> <path>:<line>`. 2 tests, 2 warrants, rubric "Sixteen" to "Seventeen
Modes". 344 pytest pass, clean.

W81 LANDED (2026-09-27): owes.git_show(rev, root) -> show(rel) for commentary_lost. The revision is
verified once (rev-parse --verify <rev>^{commit}) so a bad rev raises GitRefusedError instead of
reading as a baseline where every file is new; a path absent at a good rev is None. owes' git
refusals factored into _git_for/_run, shared with changed_files. 4 tests, 4 warrants. 348 pass.
W82 unblocked.

W82 LANDED (2026-09-27): `commentary-lost --rev R --root ROOT paths...` wired over owes.git_show;
rows `lost <origins> <text>`, `gained <text>`, `absent-before <rel>`, then a before=/after= count.
Bad rev exits 2 like owes; unread files use the merged _UNREAD reason (escapes' residue, W86's
shape). 2 tests, 2 warrants, rubric "Eighteen Modes". 350 pass, clean.
