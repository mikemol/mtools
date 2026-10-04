# W490: gmailstruct:mutants under the 60s per-mutant limit

Status: partial (finishes and passes; duration and timeout/assertion split not observable from this run)

- `bazel test //gmailstruct:mutants --test_output=errors`: PASSED. Wall time 5.431s, critical path 3.95s. The result was a **remote-cache hit** (invocation 958c1740-1dbb-45a9-97f7-514ab0ab8caf), so the test did not run again. The 5.4s is not the suite's run time.
- Test log (real path; I did not use the bazel-testlogs symlink): /var/cache/bazel-mikemol/5788f614caf7e0c338bbdcadf5d93d4f/execroot/_main/bazel-out/k8-fastbuild/testlogs/gmailstruct/mutants/test.log
  - ATTEMPTED 47 def-sites in 6 modules. KILLED 47, SURVIVED 0, ERRORED 0, UNREACHABLE 0.
  - The log does not say whether a mutant was killed by the timeout or by an assertion. 0621bf9 records a timed-out mutant as KILLED with no separate marker, so the split cannot be recovered. There is no test.xml.
- I tried a fresh run with `--nocache_test_results` to measure the duration. Hook standing rule 3 refused it ("never --nocache_test_results"). I did not work around the refusal.
- I ran `bazel build //hooks:.venv` afterwards. It is up to date.

## Residue / next steps
- W490.a: To get the duration, read the original (cache-producing) invocation's timing from BuildBuddy (see the bes-logs skill), or from the run that populated the cache after 0621bf9.
- W490.b: To split timeout kills from assertion kills, check_mutants needs to label timeout kills in its report (for example a KILLED-BY-TIMEOUT subsection). That is a code change, so it is outside this read-only card.
