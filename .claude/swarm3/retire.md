# Retire list: W494 and W496 (drafter retire; nothing was deleted)

## W494: untracked .claude/msg*.txt

Method: take each untracked file's first line and run `git log --all -F --grep=<first line> --format=%h`.
Result: 255 untracked files. 253 match a commit and 2 do not.

### Matched (file, commit, first line), safe to rm
```
.claude/msgAH.txt 65dc5e5 | mikemol-pycodemod gains alias_hint: where a call census is blind through an aliased import
.claude/msgAL.txt 215917b | mikemol-pycodemod gains aliases: every import graded by form, with locality read from the 
.claude/msgBK.txt 4690616 | mikemol-ledger, module 7: finding_bibkeys moves with its bib tool supplied by the caller, 
.claude/msgBZ.txt 019119e | .bazelrc moves the output root and the disk cache to the zram at /var/tmp and makes build-
.claude/msgCL.txt 45c8d35 | mikemol-ledger, module 12: finding_cli moves — the router that decides nothing — completin
.claude/msgCN.txt a8300bb | mikemol-ledger, module 5: finding_census moves, with the kind order a caller may extend an
.claude/msgCX.txt 158660e | mikemol-pycodemod gains crossings: every function returning a container it built, classifi
.claude/msgDC.txt cce66c4 | mikemol-pycodemod gains discards: which calls use a return value and which drop it, with a
.claude/msgDP.txt 30d6a25 | mikemol-pycodemod gains the import census: every top-level import graded against a manifes
.claude/msgEN.txt 8a279a1 | mikemol-paths-forward: --update --enables, given with no symbols, clears a waypoint's outb
.claude/msgFC.txt b993e42 | mikemol-hooks gains flag_contract: an unknown flag refused by name, and an unstated choice
.claude/msgFMT.txt cc43255 | mtools meets its own format bar: one ruff format pass over every distribution, changing la
.claude/msgFN.txt ca312cb | mikemol-pycodemod gains funcnames behind the optional extra [sqlalchemy]: it asks SQLAlche
.claude/msgHOLD.txt b8b3e41 | mikemol-membudget gains hold: the ledger without the fence, for a resource no cap can enfo
.claude/msgIN.txt 3cb24fb | mikemol-paths-forward gains --init: a fresh, empty state file, refused over an existing on
.claude/msgIP.txt 26f30a8 | mikemol-pycodemod pins the two from-import shapes summit and substrate reported the origin
.claude/msgKS.txt 0a3639e | mikemol-ledger, module 2: finding_kindspec moves, the pure kind parser whose refusal menu 
.claude/msgKW.txt ae7e6f9 | mikemol-ledger, module 11: finding_keys_show moves with the ledger named on the command li
.claude/msgKY.txt 2ed8ece | mikemol-ledger, module 4: finding_keys moves with the ledger path required — a taken set i
.claude/msgLD.txt 33005c1 | mikemol-paths-forward: --ledger accepts `-` for the queue-level symbol, since argparse eat
.claude/msgLK.txt 09d0e2d | mikemol-ledger, module 1: finding_kinds moves, with no ROOT; a witness runs where its call
.claude/msgLO.txt 22040dc | mikemol-pycodemod gains layout: every top-level statement group of a module, with an if na
.claude/msgMD.txt 7e5d7c0 | mikemol-ledger, module 9: finding_mode moves with both lenses and the runner the caller's 
.claude/msgMS.txt 1c4f500 | mikemol-pycodemod gains module_state: module-level containers classed cache / accum / cons
.claude/msgOW.txt f30ea89 | mikemol-pycodemod gains owes: the callers of a changed name in files the change did not to
.claude/msgPCA.txt ac4f358 | mikemol-pycodemod gains ambient: the cwd-dependence census really covers getcwd, skips und
.claude/msgPCB.txt 527fb4c | mikemol-pycodemod gains definitions: bindings stops counting failures as bindings and puts
.claude/msgPCC.txt 48b4cfb | mikemol-pycodemod gains commentary: the incident-log census reports unread files, and the 
.claude/msgPCD.txt 2f25797 | mikemol-pycodemod gains dead: every exemption is reported with its reason, and a quoted me
.claude/msgPCE.txt 3b712f7 | mikemol-pycodemod gains exit: the exit, catcher and interlock censuses return their own sk
.claude/msgPCG.txt faf27b4 | mikemol-pycodemod gains graph: a caller is its file and qualified scope, reaches says when
.claude/msgPCI.txt 8a0786a | mikemol-pycodemod gains imports: a dotted module query finds its importers instead of read
.claude/msgPCM.txt de84d07 | mikemol-pycodemod lands its core: `--` ends flag recognition, unread files are reported be
.claude/msgPCO.txt d348e7f | mikemol-pycodemod gains ordering: resorts takes its producer census as an argument, and an
.claude/msgPCR.txt a734d63 | mikemol-pycodemod gains arguments: forwards gains a cannot-tell side for **kwargs calls, a
.claude/msgPCS.txt 27113c5 | mikemol-pycodemod gains sites: scan returns its own query context, call facts are keyed by
.claude/msgPCT.txt 6857d33 | mikemol-pycodemod gains strings: a key write is no longer a read, a dict display declares 
.claude/msgPCW.txt c559e7e | mikemol-pycodemod gains swallows: the census of silent handlers reports the files it could
.claude/msgPFA1.txt 1b799bc | mikemol-paths-forward gains ledger.parse, the inverse of ledger.line, and the writer now e
.claude/msgPFA2.txt 2e21902 | mikemol-paths-forward --add records whether a waypoint was minted during a tick or an inte
.claude/msgPFA3.txt b46475f | mikemol-paths-forward --add refuses to re-mint a symbol a lagging counter would issue twic
.claude/msgPFA3b.txt 2293751 | mikemol-paths-forward's ledger refuses to write, and reads back as Unparsed, a stamp that 
.claude/msgPL.txt d65b020 | mikemol-ledger, module 8: finding_polarity moves, the filing-time probe that no witness is
.claude/msgPL3.txt 6bc536f | mikemol-pycodemod gains placement: when a mutation guard fires on a bare invocation, with 
.claude/msgPL4.txt 86befee | mikemol-pycodemod placement gains disagreement: the relation between a tool's intent gate 
.claude/msgR7.txt f9f0789 | mikemol-ratchet keys gains spec_for and kind_of, the two reads substrate's key_spec adds, 
.claude/msgRL.txt fbe7063 | mikemol-hooks gains refusal_log: a refused invocation recorded where its caller says, with
.claude/msgRP.txt 7ebad9b | mikemol-membudget run nests only under a parent lease in its OWN ledger, as hold does (ope
.claude/msgRR.txt 631cc60 | mikemol-ratchet gains render: every string a gate prints, the mint message fitted to the p
.claude/msgRS.txt 55812ec | mikemol-ledger, module 3: finding_restem moves whole — one finding under two spellings cou
.claude/msgRV.txt bacea13 | mikemol-ledger, module 6: finding_resolve moves whole — exact wins, a unique prefix resolv
.claude/msgRV2.txt 7acbe8b | mikemol-pycodemod gains rivals and collisions: a def that only returns a call (awaited or 
.claude/msgRX.txt 9236d5e | mikemol-paths-forward accepts another repo's waypoint, repo:W<n>, as an edge and as a ledg
.claude/msgSC.txt fc74848 | mikemol-hook-shellcheck follows sourced files (-x), so mtools' own SC1091 waiver was a che
.claude/msgSH.txt 7bd9301 | mikemol-pycodemod gains shape_sites: a line regex located in code only, with no whole-file
.claude/msgSP.txt 859a10b | mikemol-hooks pycheck refuses an edit that ADDS a line-scoped suppression — the rule its r
.claude/msgSZ.txt 04b4eca | mikemol-pycodemod gains size: every module's code lines against a per-file cap from the ca
.claude/msgTS.txt 09151ef | mikemol-transcriptstruct reports invalid UTF-8 per line instead of replacing it (TS1-d)
.claude/msgUE.txt dce1dbe | mikemol-paths-forward --update sets enables, and every mode refuses a field flag it does n
.claude/msgUN.txt 7196dc1 | mikemol-membudget gains a ledger unit: `init --unit contexts` declares what the TOTAL coun
.claude/msgVB.txt c8b48a8 | preflight builds every distribution's venv and ratchet_cli before predicting the gate, so 
.claude/msgW104.txt 11918b8 | pycodemod: Skip moves from sites into core
.claude/msgW112.txt 8aca534 | pathsforward: atomize() -- a top waypoint already advanced is flagged to split
.claude/msgW113.txt e4f478b | pathsforward: cli -- ATOMIZE wired into --check, --check-evidence, --payload
.claude/msgW114.txt 6ecf767 | pathsforward: the blocked refusal names the umbrella spelling
.claude/msgW115.txt c713252 | pathsforward: stored weight -- --update --weight N, sorted before leverage
.claude/msgW116.txt d491475 | pathsforward: --weights-from FILE.json -- bulk weights, all or nothing
.claude/msgW117.txt f945d43 | pathsforward: a metadata-only --update leaves last_worked alone
.claude/msgW118.txt 49ac0ff | pathsforward: --overlaps -- one OVERLAP line per shared touches tag
.claude/msgW121.txt 432fd5b | pathsforward: --check flags a touches tag that holds a comma
.claude/msgW122.txt 836f20e | pathsforward: --update --touches replaces the tag list
.claude/msgW123.txt f391b6a | pathsforward: the payload header carries the OVERLAP lines
.claude/msgW125.txt 6f81801 | pathsforward: --bump-blocked frees an item whose local blockers are done
.claude/msgW131.txt 4de0da4 | pathsforward: --witness QUERY stores a one-line Rego query, unread
.claude/msgW132.txt 8d9ea4e | pathsforward: --check flags a witnessed waypoint that is ready or working
.claude/msgW133.txt 345c06c | pathsforward: a witnessed waypoint is never workable
.claude/msgW174.txt 82255d0 | pathsforward: parse a touches tag's declared grain and write suffix
.claude/msgW175.txt df87d2a | pathsforward: --check flags a touches tag the W120 grammar refuses
.claude/msgW176.txt 1197fb3 | pathsforward: OVERLAP lines compare tags as parsed and mark leases
.claude/msgW177.txt c64b2e2 | pathsforward: lease.py decides leases[] over artifact writes
.claude/msgW178.txt 562c5fb | pathsforward: --lock renews the holder's leases and ledgers each lapse once
.claude/msgW179.txt 2ec718c | pre-commit: build every //<dist>:.venv before the suites read them
.claude/msgW182.txt a892cc2 | fence: acquire admits strictly in arrival order over WAIT lines
.claude/msgW183.txt cdbadf4 | pre-commit: the prebuild reads bazel's success line, not its exit code
.claude/msgW184.txt 2d15774 | pre-commit: a target-less suite refusal reaches the record (W184); bytecode cleared before
.claude/msgW185.txt 7ce6fd7 | pathsforward: --evidence-redact removes a literal, --scan-literal finds one
.claude/msgW188.txt 0430437 | pathsforward: ATOMIZE counts advances since the last split, and says so
.claude/msgW190.txt fc52dc9 | pathsforward: --status working takes leases, leaving it releases, --check lists lapsed
.claude/msgW193.txt a7e9863 | differential: the capture refuses symlinks and never follows them; py-files case 110 is wi
.claude/msgW198.txt 8a0d3fa | pytestspec: a new distribution shell for the plugin that runs Rego specs
.claude/msgW199.txt d8e5f7f | pytestspec: a .rego spec collects one item per case, and only admitted passes
.claude/msgW200.txt 754c268 | pytestspec: the default evaluator is a pinned opa, and a spec with no rules admits nothing
.claude/msgW201.txt 1bcb8a4 | pytestspec: a case declares its disposition, and each one argues itself with a reason
.claude/msgW202.txt a47fef5 | pytestspec: --impl runs an implementation on the case's fixture, so one spec judges origin
.claude/msgW203.txt 6bec251 | pytestspec: every run ends with one differential line per spec, every column stated
.claude/msgW233.txt de5715e | rules_py: every distribution's requirements.txt is checked against its uv.lock; hooks re-p
.claude/msgW246.txt 7a1167f | pathsforward --check: a blocker that is a done or dropped LOCAL symbol is a finding
.claude/msgW263.txt dd02a9f | mikemol-audiostruct: stages runs one model at a time and never lets the HF token escape
.claude/msgW267.txt 204eae8 | mikemol-audiostruct: a [gpu] extra and an audiostruct_gpu hub; bazel stages torch
.claude/msgW268.txt fdddf54 | mikemol-audiostruct: stubs for the whisperx calls the real stage factories make
.claude/msgW269.txt 26ca874 | mikemol-audiostruct: gpu.py binds whisperx's calls to the stage runner's seams
.claude/msgW273.txt 712610b | mikemol-audiostruct: cap the [gpu] extra below Python 3.14, whisperx's own limit
.claude/msgW274.txt c7fca7a | mikemol-audiostruct: stubtest holds the whisperx stubs to whisperx 3.8.6
.claude/msgW275.txt 68938e6 | mikemol-audiostruct: drop the [gpu] extra so the dev hub stops staging torch
.claude/msgW279.txt 765c1f4 | mikemol-pathsforward: --update --alarm stores VALARM triggers, refusing one with no anchor
.claude/msgW28.txt 5de9d0e | mikemol-hook-shellcheck: no waivers, ever (operator ruling 2026-09-26) — a declared table 
.claude/msgW281.txt 88851a4 | mikemol-audiostruct: run_stage runs one stage per call, handing off plain data
.claude/msgW282.txt f2892b6 | mikemol-audiostruct: the orchestrator runs each stage holding one context on the shared GP
.claude/msgW284.txt b48d34f | mikemol-audiostruct: whisperx_site is the one module that imports whisperx and torch
.claude/msgW286.txt 7159935 | mikemol-audiostruct: mikemol-audio runs the three stages end to end, one process each
.claude/msgW292.txt 2de2176 | mikemol-audiostruct: the membudget binary is a stated path, refused up front if it cannot 
.claude/msgW293.txt e8f1512 | mikemol-audiostruct: a redacted stage error names the file an OSError could not open
.claude/msgW295.txt 52a4b74 | mikemol-audiostruct: the parent re-invokes its children by its own absolute path
.claude/msgW296.txt fdf35ba | mikemol-audiostruct: records reads WhisperX words by "word", as WhisperX really emits them
.claude/msgW297.txt fde3ac7 | SKELETON.md: the absent-tests/ trap, and a norecursedirs backstop in every distribution
.claude/msgW298.txt 2415606 | mikemol-audiostruct: the torchcodec/FFmpeg warning no longer prints on every mikemol-audio
.claude/msgW299.txt 8484d08 | mikemol-pathsforward: timevalue reads RFC 5545 dates and instants, and refuses a floating 
.claude/msgW300.txt 3f7bef6 | mikemol-pathsforward: --update --dtstart and --due store RFC 5545 times on a waypoint
.claude/msgW301.txt 0c4aa27 | mikemol-pathsforward: a waypoint's status becoming done stamps COMPLETED, once
.claude/msgW303.txt 83384cc | mikemol-hooks: mikemol-gate-ledger, the pre-commit gate ledger, with the ledger path a req
.claude/msgW305.txt a2b7b62 | mikemol-pathsforward: --update SYMBOL --caused-by REF fixes a mis-cited cause in place
.claude/msgW306.txt e4fe93b | mikemol-pycodemod: header mode checks the licence header, or writes the lines a file is mi
.claude/msgW307.txt bd422f3 | mikemol-pathsforward: --alarm -PT1H is read as a value, not an unknown option
.claude/msgW308.txt f22d7fe | mikemol-pathsforward: timevalue.fires_at resolves an alarm to its UTC instant
.claude/msgW309.txt ffc7896 | mikemol-pathsforward: --update --rrule and --exdate store a recurrence, checked against RF
.claude/msgW310.txt aac3a28 | mikemol-pathsforward: --complete-occurrence marks one occurrence of a recurring waypoint d
.claude/msgW312.txt 7647f7c | mikemol-pathsforward: ics writes RFC 5545 content lines, escaped, folded at 75 octets, in 
.claude/msgW313.txt 36ee26f | mikemol-pathsforward: --ics prints the queue as an iCalendar file, one VTODO per waypoint
.claude/msgW314.txt 632a0a5 | mikemol-pathsforward: --ics carries RRULE, EXDATE, VALARM and a COMPLETED override per occ
.claude/msgW315.txt 0405fda | mikemol-pathsforward: --ics emits one VTIMEZONE per TZID it uses, built from the system zo
.claude/msgW316.txt 1bd18ae | mikemol-pytestspec: the differential line survives pytest-xdist, merged on the controller
.claude/msgW323.txt 9ab6a85 | mtools: the bazel python rules become their own Bazel module, mikemol_rules_py
.claude/msgW324.txt 3ac8ac1 | mtools: the ruff check becomes its own Bazel module, mikemol_check_ruff, owning its pinned
.claude/msgW325.txt 372ec21 | mtools: the mypy check becomes its own Bazel module, and every atom file is checked by lab
.claude/msgW326.txt c07542a | mtools: the mutation check becomes its own Bazel module, carrying its test and the root's 
.claude/msgW327.txt cd61477 | mtools: the ratchet check becomes its own Bazel module, the last of the five shared checks
.claude/msgW328.txt 766029b | mtools: the commit gate's warrant ledger counts atoms too, derived from */MODULE.bazel
.claude/msgW33.txt 1dcb200 | pycodemod: cli.py — the driver's first slice, three modes and every retired/DO-NOT-PORT re
.claude/msgW331.txt 074eecc | mtools: draft of the reusable module gate workflow, every job told its size (not wired, no
.claude/msgW332.txt 1ecff9a | ci: the reusable gate workflow is under a pinned actionlint, armed on every run
.claude/msgW333.txt b107ad6 | mikemol-gmailstruct stage 1: records.message puts each Gmail messages.get response in exac
.claude/msgW334.txt f667f06 | mikemol-gmailstruct: records.pages puts every listed message in exactly one record and say
.claude/msgW335.txt 01cdf6f | mikemol-gmailstruct: records.parts puts every node of a message's MIME tree in exactly one
.claude/msgW341.txt 5135a50 | mtools: the python rules atom gains venv_check, which checks one distribution's built venv
.claude/msgW342.txt 76bc7af | mtools: gmailstruct's built venv is checked by its own bazel test, through a venv_check dr
.claude/msgW343.txt 5c156fb | mtools: hooks' venv tests stop sweeping every distribution; each distribution's own venv t
.claude/msgW349.txt 8d4b9ca | mtools: every distribution's built venv is checked by its own bazel test
.claude/msgW34b.txt eeb9c18 | pycodemod: cli.py — attr-reads and importers wired, RETIRED empties out
.claude/msgW34e.txt 34f04c6 | pycodemod: cli.py — disagreement wired, driver now nine modes
.claude/msgW34f.txt a726f33 | pycodemod: cli.py — placement wired, driver now ten modes
.claude/msgW34g.txt db5abce | pycodemod: cli.py — modstate wired, driver now eleven modes
.claude/msgW35.txt 4a4162e | pycodemod: BUILD.bazel — the dist venv carries mikemol-pycodemod
.claude/msgW350.txt e6161eb | rules_py/venv_check: a suite that cannot collect is named with pytest's own words
.claude/msgW351.txt 6e9e17b | mikemol-gmailstruct: auth.decrypt brings the refresh token from its age file into memory o
.claude/msgW352.txt 7381736 | mikemol-gmailstruct: auth.exchange turns the refresh token into an in-memory access token,
.claude/msgW353.txt a924508 | mikemol-gmailstruct: consent runs the one-time OAuth flow and hands the refresh token only
.claude/msgW354.txt 63d7873 | pathsforward: --vectors-from sets many WV:1 vectors in one write; --repair-counter raises 
.claude/msgW356.txt f272ed4 | mikemol-gmailstruct: the mikemol-gmail consent command, the one-time step the operator run
.claude/msgW357.txt e11ba1b | mikemol-gmailstruct: fetch reads Gmail list pages and messages into records, and a failed 
.claude/msgW358.txt 1b8d10b | mikemol-gmailstruct: mikemol-gmail raw writes one message as its exact RFC 822 bytes, owne
.claude/msgW359.txt 0621bf9 | check_mutants: each mutant's suite runs under a time limit; one that outlives it is record
.claude/msgW360.txt 7c5070d | mikemol-gmailstruct: mikemol-gmail search and show, printing Gmail records as JSON lines w
.claude/msgW362.txt 00c1b3b | rules_py: suite_check checks one distribution's suite runs under pytest and never resolves
.claude/msgW363.txt 16e8a22 | rules_py: suite_check refuses a population negative with nothing truthy beside it, per dis
.claude/msgW365.txt 7f3632f | gmailstruct: //gmailstruct:suite runs suite_check over its own BUILD and tests
.claude/msgW366.txt f3c5c76 | hooks: //hooks:suite runs suite_check over its own BUILD and tests
.claude/msgW367.txt 59f302b | mdstruct: //mdstruct:suite runs suite_check over its own BUILD and tests
.claude/msgW368.txt fe5d423 | ratchet: //ratchet:suite runs suite_check over its own BUILD and tests
.claude/msgW369.txt 1042a93 | fence: //fence:suite runs suite_check over its own BUILD and tests
.claude/msgW370.txt 5da58c1 | the remaining 9 distributions run :suite, so all 14 now check their own suite (W362)
.claude/msgW371.txt 03836cc | hooks: test_bar_fires' two suite sweeps become one boundary check, that every distribution
.claude/msgW372.txt 7b1e381 | pytestspec: a case's expect.deny passes only when exactly those rule ids deny it, so a ref
.claude/msgW374.txt a70989c | pytestspec: the outcome -> column map is declared total, not probed from failure text
.claude/msgW375.txt 9399d7c | rules_py: dist_checks() declares a distribution's :venv and :suite together; gmailstruct c
.claude/msgW376.txt 0ba1cfc | the other 13 distributions call dist_checks(), so no hand-written :venv or :suite block re
.claude/msgW377.txt d906a88 | pathsforward payload: a last rung drops the done list's symbols and keeps its count
.claude/msgW380.txt ac59711 | pytestspec: pytestspec_data declares rego libraries loaded beside every spec, so a spec ca
.claude/msgW381.txt cec108a | pytestspec: expect.withheld beside expect.deny, and every passing case lands in exactly on
.claude/msgW382.txt f342cea | gmailstruct: age's YubiKey prompts reach the terminal, and a decrypt failure names age's o
.claude/msgW383.txt 30d3fc9 | gmailstruct: consent writes the .age refresh token owner-only, never under the umask
.claude/msgW384.txt 2ab92ab | check_ruff: selector_check.py refuses a selector whose comment still cites a code the sele
.claude/msgW385.txt 5b3c9ca | check_ruff: suppression_check.py, every ruff: ignore directive in a distribution is honour
.claude/msgW386.txt 1ccf532 | every distribution runs both ruff-config checks via dist_checks(), and test_bar_fires drop
.claude/msgW388.txt d4ecf7f | check_ratchet: refusal_check.py, a distribution's ratchet must refuse a planted finding by
.claude/msgW389.txt 3e12e44 | every distribution runs the ratchet refusal check via dist_checks(), and test_bar_fires dr
.claude/msgW427.txt 6c242bb | fence: mikemol-membudget peaks [PREFIX] reads the run ledger bash would read
.claude/msgW439.txt 5447a09 | pycodemod/differential: swarm batch tq1 - binding, funcnames, source under --impl subject
.claude/msgW440.txt 710d043 | pycodemod/differential: swarm batch tq2 - reifies and ambient under --impl subject
.claude/msgW444.txt 0102a4e | pycodemod/differential: swarm batch tq4 - size, state, crossings, importers, aliases under
.claude/msgW446.txt 6b394dc | pycodemod/differential: swarm batch tq5 - swallows, writes_by_default; py-files and f5 dec
.claude/msgW459.txt 03fac34 | pytestspec: do-not-port deselects under every --impl but the origin
.claude/msgW46.txt 22a0c40 | pycodemod: report.incomplete(skipped, population) -- one shared incomplete-scan banner
.claude/msgW460.txt de1d4fd | pycodemod/differential: swarm batch tq3 - callgraph, reaches, forwards, asserted under --i
.claude/msgW467.txt bebafd7 | pycodemod/differential: track the W206 differential's Rego specs and case data
.claude/msgW468.txt 2737143 | pycodemod/differential: track the differential's adapters (conftest.py), clean under pycod
.claude/msgW469.txt a838c40 | pycodemod/differential: retire the .claude/design harness; the tracked home is the only on
.claude/msgW47.txt 2596184 | fence: WAIT lines are a parsed ledger kind, rendered and gc-reaped
.claude/msgW470.txt 564dfc2 | pycodemod/differential: track the case generator and its two inputs
.claude/msgW471.txt 1aef704 | pycodemod/differential: track the replay probe peek.py, with its failures named
.claude/msgW472.txt 572e155 | pycodemod/differential: track the origin capture tracer as capture.py, typed and clean
.claude/msgW474.txt 09eb5d2 | pre-commit: the ratchet's refusal reaches the verdict instead of killing the gate under se
.claude/msgW475.txt 33a17aa | pycodemod/differential: track the capture comparator; capture.py proved equivalent to 0 ro
.claude/msgW476.txt 6e7fd2c | pycodemod: the ruff, mypy and ratchet targets reach differential/
.claude/msgW477.txt 5cf82d5 | check_ruff: every ruff target also runs ruff format --check
.claude/msgW478.txt 7ba8382 | pycodemod: opa test over the differential's Rego specs is a bazel test, on a pinned opa
.claude/msgW480.txt 9dc1a76 | differential conftest: the port's equivalent of _cached_defs, so binding 209-211 are judge
.claude/msgW481.txt 5520a72 | differential size.rego: case 146 denies when no row names the guards, including no row at 
.claude/msgW482.txt 42619eb | hooks/pycheck: an atom's own mypy.ini governs its files, as the gate's mypy target does
.claude/msgW51.txt 8c24617 | pathsforward: model.leverage/describe_rank — ordered() gains a leverage tiebreak, the queu
.claude/msgW52.txt c6753af | pycodemod: cli.py — layout wired, driver now twelve modes
.claude/msgW53.txt 47597f9 | pycodemod: cli.py — collisions wired, paths-only subparsers table-driven
.claude/msgW54.txt 5db27e4 | pycodemod: cli.py — reifies wired, driver now fourteen modes
.claude/msgW55.txt 2ca003b | pycodemod: cli.py — escapes wired, driver now fifteen modes
.claude/msgW56.txt 5bb85e8 | pycodemod: cli.py — catchers wired, driver now sixteen modes
.claude/msgW57.txt 9493823 | pycodemod: cli.py — interlock wired, driver now seventeen modes
.claude/msgW58.txt 02dd6eb | pycodemod: cli.py — ambient wired, driver now nineteen modes
.claude/msgW59.txt 7938a48 | pycodemod: cli.py — callgraph wired, driver now twenty modes
.claude/msgW60.txt ebc71ac | pycodemod: cli.py — reaches wired, driver now twenty-one modes
.claude/msgW61.txt 9f667e9 | pycodemod: cli.py — guarded wired, driver now twenty-two modes
.claude/msgW62.txt f202fd9 | pycodemod: cli.py — key-reads wired, driver now twenty-three modes
.claude/msgW63.txt 1c70420 | pycodemod: cli.py — bindings wired, driver now twenty-four modes
.claude/msgW64.txt f6e7788 | pycodemod: cli.py — aliases wired, driver now twenty-five modes
.claude/msgW65.txt 4160ead | pycodemod: cli.py — funcnames wired, driver now twenty-six modes
.claude/msgW66.txt 73f54f6 | pycodemod: cli.py — size wired, driver now twenty-seven modes
.claude/msgW67.txt 4d9f975 | pycodemod: cli.py — deps wired, driver now twenty-eight modes
.claude/msgW68.txt d6ca0f5 | pycodemod: cli.py — crossings wired, driver now twenty-nine modes
.claude/msgW69.txt 46380da | pycodemod: cli.py — shapes wired, driver now thirty modes
.claude/msgW70.txt 5fbaed3 | pycodemod: cli.py — commentary wired, driver now thirty-one modes
.claude/msgW71.txt 9c0e7e9 | pycodemod: cli.py — discards wired, driver now thirty-two modes
.claude/msgW72.txt 09cfb09 | pycodemod: cli.py — fix-owes-callers redirects to owes
.claude/msgW73.txt e6aee74 | pycodemod: cli.py — forwards wired, driver now thirty-three modes
.claude/msgW74.txt 2732c9b | pycodemod: cli.py — asserted wired, driver now thirty-four modes
.claude/msgW75.txt 37d90f7 | pycodemod: cli.py — values wired, driver now thirty-five modes
.claude/msgW76.txt 651230c | pycodemod: cli.py — literals wired, driver now thirty-six modes
.claude/msgW77.txt cb0f553 | pycodemod: cli.py — source-of wired, driver now thirty-nine modes
.claude/msgW78.txt ee68860 | pycodemod: cli.py — alias-hint wired, driver now forty modes
.claude/msgW79.txt ad20a68 | pycodemod: cli.py — commentary-kinds wired, driver now thirty-seven modes
.claude/msgW80.txt ff30847 | pycodemod: cli.py — commentary-blocks wired, driver now thirty-eight modes
.claude/msgW81.txt 4517c68 | pycodemod: owes.git_show — the git-show adapter commentary_lost needs
.claude/msgW82.txt 79baaf6 | pycodemod: cli.py — commentary-lost wired, driver now eighteen modes
.claude/msgW83.txt 89b9e13 | pycodemod: cli.py — rivals wired, driver now forty-one modes
.claude/msgW84.txt 29972b6 | pycodemod: cli.py — resorts wired, driver now forty-two modes
.claude/msgW85.txt 9d72487 | pycodemod: cli.py — writes wired, driver now forty-three modes
.claude/msgW87.txt 296fa03 | pycodemod: the deps, crossings and literals happy paths pin row content
.claude/msgW91.txt cd142c9 | pytest: empty_parameter_set_mark = fail_at_collect in all ten distributions
.claude/msgW92.txt ec254f9 | pycodemod: commentary._read returns str | Skip, not None
.claude/msgW93.txt e227916 | pycodemod: Census carries skipped Skips; commentary reports per reason
.claude/msgW94.txt b7a9332 | pycodemod: Lost carries skipped Skips; commentary-lost reports per reason
.claude/msgW95.txt 717159e | pycodemod: Kinds carries skipped Skips
.claude/msgW96.txt 39113cb | pycodemod: Blocks carries skipped Skips; W86 closes
.claude/msgW97.txt 7dd4b7b | pycodemod: escapes carries skipped Skips, reported per reason
.claude/msgW98.txt 55edb9a | pycodemod: cli.py drops _UNREAD, which nothing reads
.claude/msgWR.txt de104f6 | mikemol-pycodemod gains writes_by_default: could a bare run write a real file, read from t
```

### Unmatched, KEEP
- .claude/msgW173a.txt: the message for the pending commit that untracks msgW34c/d. Those deletions are staged (`D`) and not yet committed. Retire it after that commit lands.
- .claude/msgGE.txt: the unsent peer letter to substrate about --guarded. It is owned by W495. Retire it only after it is sent.

### rm command (W494)
```
rm -- /home/mikemol/github/mtools/.claude/msgAH.txt /home/mikemol/github/mtools/.claude/msgAL.txt /home/mikemol/github/mtools/.claude/msgBK.txt /home/mikemol/github/mtools/.claude/msgBZ.txt /home/mikemol/github/mtools/.claude/msgCL.txt /home/mikemol/github/mtools/.claude/msgCN.txt /home/mikemol/github/mtools/.claude/msgCX.txt /home/mikemol/github/mtools/.claude/msgDC.txt /home/mikemol/github/mtools/.claude/msgDP.txt /home/mikemol/github/mtools/.claude/msgEN.txt /home/mikemol/github/mtools/.claude/msgFC.txt /home/mikemol/github/mtools/.claude/msgFMT.txt /home/mikemol/github/mtools/.claude/msgFN.txt /home/mikemol/github/mtools/.claude/msgHOLD.txt /home/mikemol/github/mtools/.claude/msgIN.txt /home/mikemol/github/mtools/.claude/msgIP.txt /home/mikemol/github/mtools/.claude/msgKS.txt /home/mikemol/github/mtools/.claude/msgKW.txt /home/mikemol/github/mtools/.claude/msgKY.txt /home/mikemol/github/mtools/.claude/msgLD.txt /home/mikemol/github/mtools/.claude/msgLK.txt /home/mikemol/github/mtools/.claude/msgLO.txt /home/mikemol/github/mtools/.claude/msgMD.txt /home/mikemol/github/mtools/.claude/msgMS.txt /home/mikemol/github/mtools/.claude/msgOW.txt /home/mikemol/github/mtools/.claude/msgPCA.txt /home/mikemol/github/mtools/.claude/msgPCB.txt /home/mikemol/github/mtools/.claude/msgPCC.txt /home/mikemol/github/mtools/.claude/msgPCD.txt /home/mikemol/github/mtools/.claude/msgPCE.txt /home/mikemol/github/mtools/.claude/msgPCG.txt /home/mikemol/github/mtools/.claude/msgPCI.txt /home/mikemol/github/mtools/.claude/msgPCM.txt /home/mikemol/github/mtools/.claude/msgPCO.txt /home/mikemol/github/mtools/.claude/msgPCR.txt /home/mikemol/github/mtools/.claude/msgPCS.txt /home/mikemol/github/mtools/.claude/msgPCT.txt /home/mikemol/github/mtools/.claude/msgPCW.txt /home/mikemol/github/mtools/.claude/msgPFA1.txt /home/mikemol/github/mtools/.claude/msgPFA2.txt /home/mikemol/github/mtools/.claude/msgPFA3.txt /home/mikemol/github/mtools/.claude/msgPFA3b.txt /home/mikemol/github/mtools/.claude/msgPL.txt /home/mikemol/github/mtools/.claude/msgPL3.txt /home/mikemol/github/mtools/.claude/msgPL4.txt /home/mikemol/github/mtools/.claude/msgR7.txt /home/mikemol/github/mtools/.claude/msgRL.txt /home/mikemol/github/mtools/.claude/msgRP.txt /home/mikemol/github/mtools/.claude/msgRR.txt /home/mikemol/github/mtools/.claude/msgRS.txt /home/mikemol/github/mtools/.claude/msgRV.txt /home/mikemol/github/mtools/.claude/msgRV2.txt /home/mikemol/github/mtools/.claude/msgRX.txt /home/mikemol/github/mtools/.claude/msgSC.txt /home/mikemol/github/mtools/.claude/msgSH.txt /home/mikemol/github/mtools/.claude/msgSP.txt /home/mikemol/github/mtools/.claude/msgSZ.txt /home/mikemol/github/mtools/.claude/msgTS.txt /home/mikemol/github/mtools/.claude/msgUE.txt /home/mikemol/github/mtools/.claude/msgUN.txt /home/mikemol/github/mtools/.claude/msgVB.txt /home/mikemol/github/mtools/.claude/msgW104.txt /home/mikemol/github/mtools/.claude/msgW112.txt /home/mikemol/github/mtools/.claude/msgW113.txt /home/mikemol/github/mtools/.claude/msgW114.txt /home/mikemol/github/mtools/.claude/msgW115.txt /home/mikemol/github/mtools/.claude/msgW116.txt /home/mikemol/github/mtools/.claude/msgW117.txt /home/mikemol/github/mtools/.claude/msgW118.txt /home/mikemol/github/mtools/.claude/msgW121.txt /home/mikemol/github/mtools/.claude/msgW122.txt /home/mikemol/github/mtools/.claude/msgW123.txt /home/mikemol/github/mtools/.claude/msgW125.txt /home/mikemol/github/mtools/.claude/msgW131.txt /home/mikemol/github/mtools/.claude/msgW132.txt /home/mikemol/github/mtools/.claude/msgW133.txt /home/mikemol/github/mtools/.claude/msgW174.txt /home/mikemol/github/mtools/.claude/msgW175.txt /home/mikemol/github/mtools/.claude/msgW176.txt /home/mikemol/github/mtools/.claude/msgW177.txt /home/mikemol/github/mtools/.claude/msgW178.txt /home/mikemol/github/mtools/.claude/msgW179.txt /home/mikemol/github/mtools/.claude/msgW182.txt /home/mikemol/github/mtools/.claude/msgW183.txt /home/mikemol/github/mtools/.claude/msgW184.txt /home/mikemol/github/mtools/.claude/msgW185.txt /home/mikemol/github/mtools/.claude/msgW188.txt /home/mikemol/github/mtools/.claude/msgW190.txt /home/mikemol/github/mtools/.claude/msgW193.txt /home/mikemol/github/mtools/.claude/msgW198.txt /home/mikemol/github/mtools/.claude/msgW199.txt /home/mikemol/github/mtools/.claude/msgW200.txt /home/mikemol/github/mtools/.claude/msgW201.txt /home/mikemol/github/mtools/.claude/msgW202.txt /home/mikemol/github/mtools/.claude/msgW203.txt /home/mikemol/github/mtools/.claude/msgW233.txt /home/mikemol/github/mtools/.claude/msgW246.txt /home/mikemol/github/mtools/.claude/msgW263.txt /home/mikemol/github/mtools/.claude/msgW267.txt /home/mikemol/github/mtools/.claude/msgW268.txt /home/mikemol/github/mtools/.claude/msgW269.txt /home/mikemol/github/mtools/.claude/msgW273.txt /home/mikemol/github/mtools/.claude/msgW274.txt /home/mikemol/github/mtools/.claude/msgW275.txt /home/mikemol/github/mtools/.claude/msgW279.txt /home/mikemol/github/mtools/.claude/msgW28.txt /home/mikemol/github/mtools/.claude/msgW281.txt /home/mikemol/github/mtools/.claude/msgW282.txt /home/mikemol/github/mtools/.claude/msgW284.txt /home/mikemol/github/mtools/.claude/msgW286.txt /home/mikemol/github/mtools/.claude/msgW292.txt /home/mikemol/github/mtools/.claude/msgW293.txt /home/mikemol/github/mtools/.claude/msgW295.txt /home/mikemol/github/mtools/.claude/msgW296.txt /home/mikemol/github/mtools/.claude/msgW297.txt /home/mikemol/github/mtools/.claude/msgW298.txt /home/mikemol/github/mtools/.claude/msgW299.txt /home/mikemol/github/mtools/.claude/msgW300.txt /home/mikemol/github/mtools/.claude/msgW301.txt /home/mikemol/github/mtools/.claude/msgW303.txt /home/mikemol/github/mtools/.claude/msgW305.txt /home/mikemol/github/mtools/.claude/msgW306.txt /home/mikemol/github/mtools/.claude/msgW307.txt /home/mikemol/github/mtools/.claude/msgW308.txt /home/mikemol/github/mtools/.claude/msgW309.txt /home/mikemol/github/mtools/.claude/msgW310.txt /home/mikemol/github/mtools/.claude/msgW312.txt /home/mikemol/github/mtools/.claude/msgW313.txt /home/mikemol/github/mtools/.claude/msgW314.txt /home/mikemol/github/mtools/.claude/msgW315.txt /home/mikemol/github/mtools/.claude/msgW316.txt /home/mikemol/github/mtools/.claude/msgW323.txt /home/mikemol/github/mtools/.claude/msgW324.txt /home/mikemol/github/mtools/.claude/msgW325.txt /home/mikemol/github/mtools/.claude/msgW326.txt /home/mikemol/github/mtools/.claude/msgW327.txt /home/mikemol/github/mtools/.claude/msgW328.txt /home/mikemol/github/mtools/.claude/msgW33.txt /home/mikemol/github/mtools/.claude/msgW331.txt /home/mikemol/github/mtools/.claude/msgW332.txt /home/mikemol/github/mtools/.claude/msgW333.txt /home/mikemol/github/mtools/.claude/msgW334.txt /home/mikemol/github/mtools/.claude/msgW335.txt /home/mikemol/github/mtools/.claude/msgW341.txt /home/mikemol/github/mtools/.claude/msgW342.txt /home/mikemol/github/mtools/.claude/msgW343.txt /home/mikemol/github/mtools/.claude/msgW349.txt /home/mikemol/github/mtools/.claude/msgW34b.txt /home/mikemol/github/mtools/.claude/msgW34e.txt /home/mikemol/github/mtools/.claude/msgW34f.txt /home/mikemol/github/mtools/.claude/msgW34g.txt /home/mikemol/github/mtools/.claude/msgW35.txt /home/mikemol/github/mtools/.claude/msgW350.txt /home/mikemol/github/mtools/.claude/msgW351.txt /home/mikemol/github/mtools/.claude/msgW352.txt /home/mikemol/github/mtools/.claude/msgW353.txt /home/mikemol/github/mtools/.claude/msgW354.txt /home/mikemol/github/mtools/.claude/msgW356.txt /home/mikemol/github/mtools/.claude/msgW357.txt /home/mikemol/github/mtools/.claude/msgW358.txt /home/mikemol/github/mtools/.claude/msgW359.txt /home/mikemol/github/mtools/.claude/msgW360.txt /home/mikemol/github/mtools/.claude/msgW362.txt /home/mikemol/github/mtools/.claude/msgW363.txt /home/mikemol/github/mtools/.claude/msgW365.txt /home/mikemol/github/mtools/.claude/msgW366.txt /home/mikemol/github/mtools/.claude/msgW367.txt /home/mikemol/github/mtools/.claude/msgW368.txt /home/mikemol/github/mtools/.claude/msgW369.txt /home/mikemol/github/mtools/.claude/msgW370.txt /home/mikemol/github/mtools/.claude/msgW371.txt /home/mikemol/github/mtools/.claude/msgW372.txt /home/mikemol/github/mtools/.claude/msgW374.txt /home/mikemol/github/mtools/.claude/msgW375.txt /home/mikemol/github/mtools/.claude/msgW376.txt /home/mikemol/github/mtools/.claude/msgW377.txt /home/mikemol/github/mtools/.claude/msgW380.txt /home/mikemol/github/mtools/.claude/msgW381.txt /home/mikemol/github/mtools/.claude/msgW382.txt /home/mikemol/github/mtools/.claude/msgW383.txt /home/mikemol/github/mtools/.claude/msgW384.txt /home/mikemol/github/mtools/.claude/msgW385.txt /home/mikemol/github/mtools/.claude/msgW386.txt /home/mikemol/github/mtools/.claude/msgW388.txt /home/mikemol/github/mtools/.claude/msgW389.txt /home/mikemol/github/mtools/.claude/msgW427.txt /home/mikemol/github/mtools/.claude/msgW439.txt /home/mikemol/github/mtools/.claude/msgW440.txt /home/mikemol/github/mtools/.claude/msgW444.txt /home/mikemol/github/mtools/.claude/msgW446.txt /home/mikemol/github/mtools/.claude/msgW459.txt /home/mikemol/github/mtools/.claude/msgW46.txt /home/mikemol/github/mtools/.claude/msgW460.txt /home/mikemol/github/mtools/.claude/msgW467.txt /home/mikemol/github/mtools/.claude/msgW468.txt /home/mikemol/github/mtools/.claude/msgW469.txt /home/mikemol/github/mtools/.claude/msgW47.txt /home/mikemol/github/mtools/.claude/msgW470.txt /home/mikemol/github/mtools/.claude/msgW471.txt /home/mikemol/github/mtools/.claude/msgW472.txt /home/mikemol/github/mtools/.claude/msgW474.txt /home/mikemol/github/mtools/.claude/msgW475.txt /home/mikemol/github/mtools/.claude/msgW476.txt /home/mikemol/github/mtools/.claude/msgW477.txt /home/mikemol/github/mtools/.claude/msgW478.txt /home/mikemol/github/mtools/.claude/msgW480.txt /home/mikemol/github/mtools/.claude/msgW481.txt /home/mikemol/github/mtools/.claude/msgW482.txt /home/mikemol/github/mtools/.claude/msgW51.txt /home/mikemol/github/mtools/.claude/msgW52.txt /home/mikemol/github/mtools/.claude/msgW53.txt /home/mikemol/github/mtools/.claude/msgW54.txt /home/mikemol/github/mtools/.claude/msgW55.txt /home/mikemol/github/mtools/.claude/msgW56.txt /home/mikemol/github/mtools/.claude/msgW57.txt /home/mikemol/github/mtools/.claude/msgW58.txt /home/mikemol/github/mtools/.claude/msgW59.txt /home/mikemol/github/mtools/.claude/msgW60.txt /home/mikemol/github/mtools/.claude/msgW61.txt /home/mikemol/github/mtools/.claude/msgW62.txt /home/mikemol/github/mtools/.claude/msgW63.txt /home/mikemol/github/mtools/.claude/msgW64.txt /home/mikemol/github/mtools/.claude/msgW65.txt /home/mikemol/github/mtools/.claude/msgW66.txt /home/mikemol/github/mtools/.claude/msgW67.txt /home/mikemol/github/mtools/.claude/msgW68.txt /home/mikemol/github/mtools/.claude/msgW69.txt /home/mikemol/github/mtools/.claude/msgW70.txt /home/mikemol/github/mtools/.claude/msgW71.txt /home/mikemol/github/mtools/.claude/msgW72.txt /home/mikemol/github/mtools/.claude/msgW73.txt /home/mikemol/github/mtools/.claude/msgW74.txt /home/mikemol/github/mtools/.claude/msgW75.txt /home/mikemol/github/mtools/.claude/msgW76.txt /home/mikemol/github/mtools/.claude/msgW77.txt /home/mikemol/github/mtools/.claude/msgW78.txt /home/mikemol/github/mtools/.claude/msgW79.txt /home/mikemol/github/mtools/.claude/msgW80.txt /home/mikemol/github/mtools/.claude/msgW81.txt /home/mikemol/github/mtools/.claude/msgW82.txt /home/mikemol/github/mtools/.claude/msgW83.txt /home/mikemol/github/mtools/.claude/msgW84.txt /home/mikemol/github/mtools/.claude/msgW85.txt /home/mikemol/github/mtools/.claude/msgW87.txt /home/mikemol/github/mtools/.claude/msgW91.txt /home/mikemol/github/mtools/.claude/msgW92.txt /home/mikemol/github/mtools/.claude/msgW93.txt /home/mikemol/github/mtools/.claude/msgW94.txt /home/mikemol/github/mtools/.claude/msgW95.txt /home/mikemol/github/mtools/.claude/msgW96.txt /home/mikemol/github/mtools/.claude/msgW97.txt /home/mikemol/github/mtools/.claude/msgW98.txt /home/mikemol/github/mtools/.claude/msgWR.txt
```

## W496

- .claude/paths_forward_render.py: SAFE. It is untracked. `git grep` finds no caller, only standing.rego rule 11 and its tests in standing_test.rego. Those deny running it ("retired; use mikemol-paths-forward"), and they match by regex, so they do not need the file to exist.
- .claude/preamble.txt: NOT SAFE as-is. Its text DIFFERS from the `preamble` field in paths-forward.json. It may be a draft that was never applied, or a stale copy. The integrator should diff the two, apply any wanted text through mikemol-paths-forward, and then rm it.
- .claude/design/__pycache__/: SAFE. It is ignored (`!!`) and holds only W128-capture.cpython-314.pyc. Its source was retired by a838c40 and replaced by the tracked capture.py (572e155).
- .claude/swarm/ (tq1-5): SAFE. All five batch commits landed (5447a09, 710d043, de1d4fd, 0102a4e, 6b394dc). In each tq*-cases dir, 69 of 82 files are byte-identical to tracked files. 12 of the other 13 are byte-identical to earlier committed versions of pycodemod/differential/* (they were edited later, for example by 5520a72). The 13th, conftest.py, matches no committed blob. It is a pre-tracking draft that the tracked pycodemod/differential/conftest.py (2737143, 9dc1a76) supersedes. This is the one judgment call. tq*.md are the swarm reports for batches that have landed. Each tq*-cases/__pycache__ is ignored.

### rm command (W496)
```
rm -- /home/mikemol/github/mtools/.claude/paths_forward_render.py
rm -r -- /home/mikemol/github/mtools/.claude/design/__pycache__
rm -r -- /home/mikemol/github/mtools/.claude/swarm
```
(preamble.txt is held, see above)
