#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑⚑ A STANDING WITNESS ON A CHECKER'S DOMAIN. An action's verdict ranges over its DECLARED
# inputs, so a checker whose declaration is short of its real domain returns a stale green for
# every input it cannot see. mypy is the case that matters here, because it is the one checker
# whose verdict on a file depends on files it does not name: editing an imported module changes
# the importer's type-correctness while leaving its bytes untouched.
#
# ⚑⚑ THE CLAIM WAS TRUE AND UNARMED, WHICH IS THE STATE THIS REPOSITORY REFUSES ELSEWHERE. The
# BUILD file declares `glob(["src/**/*.py", ...])` — structurally right, and never once tested
# against a transitive edit. A glob that silently stopped matching, a `srcs` narrowed during a
# refactor, or a distribution added without the pattern would each produce a green mypy over a
# domain smaller than the type checker's own.
#
# ⚑ AND A ONE-ARMED VERSION OF THIS WITNESS IS WORSE THAN NONE. Asserting only that the action
# RE-RUNS proves the file is an input; asserting only that mypy FAILS proves mypy works. Neither
# alone proves the DOMAIN is complete — the pair does: a transitive edit must reach the action,
# and a transitive DEFECT must reach the verdict.
set -uo pipefail

dist="${1:?the distribution directory was not passed}"
target="${2:?the mypy target was not passed}"
victim="${3:?the transitive module was not passed}"

cd "$(dirname "$0")" || exit 1
restore() { git checkout "$victim" 2>/dev/null; }
trap restore EXIT

fail=0
say() { printf '  %s\n' "$*"; }

# ⚑ THE CONTROL RUNS FIRST AND MUST PASS. An arm measured against an already-red tree reports the
# pre-existing failure as its own finding — and every subsequent arm agrees for the wrong reason.
if ! bazel test "$target" >/dev/null 2>&1; then
    say "CONTROL FAILED: $target is red BEFORE the probe — the arms below would be meaningless"
    exit 1
fi

# ⚑⚑ ARM 1 — REACHABILITY. A CONTENT change (not `touch`: bazel keys on bytes, so an mtime bump
# invalidates nothing and an arm built on one measures the clock, not the graph).
# ⚑⚑⚑ THE PROBE CARRIES A NONCE, AND WITHOUT ONE THIS ARM IS UNFALSIFIABLE-GREEN'S TWIN: A
# PERMANENT FALSE RED. A fixed probe string is a digest the cache has already seen, so the second
# run of this witness is served from the remote cache — `Executed 0 out of 1` — and the arm
# concludes the file is outside the domain. Measured: identical `# probe` appends returned
# `Executed 0` while a nonce-carrying append returned `1 linux-sandbox`, same file, seconds apart.
#
# ⚑⚑ AND THE TWO EXPLANATIONS ARE INDISTINGUISHABLE IN THE OUTPUT THIS ARM READS. "Not an input"
# and "already answered" both print `Executed 0`. A witness that cannot separate them is not
# measuring the domain — it is measuring whether it has run before, which is the one question it
# was not asked.
printf '\n# transient domain probe %s\n' "$(date +%s%N)" >> "$victim"
# ⚑⚑⚑ THE OUTPUT IS CAPTURED, THEN MATCHED — NEVER `bazel | grep -q`. Under `pipefail`, a `grep -q`
# that MATCHES closes the pipe, bazel takes SIGPIPE, and the pipeline reports bazel's death as the
# verdict: the arm fails precisely BECAUSE it found what it was looking for. Measured here — both
# arms of this witness reported FAILED against a tree that had passed the same probes by hand
# minutes earlier. That is this repository's Rule 14 defect (the reporter's status standing in for
# the subject's) reappearing inside the witness written to enforce the rule it belongs to.
out="$(bazel test "$target" 2>&1)"
if printf '%s' "$out" | grep -q "Executed 1 out of 1 test"; then
    say "arm 1 REACHABILITY: a transitive content change re-executes the action"
else
    say "arm 1 FAILED: editing $victim did NOT invalidate $target — it is outside the domain"
    fail=1
fi
restore

# ⚑⚑ ARM 2 — VERDICT. Reachability alone only proves the bytes are keyed; this proves the checker
# actually ranges over them.
cat >> "$victim" <<'PROBE'


def _transient_domain_probe() -> int:
    return "not an int"
PROBE
out="$(bazel test "$target" 2>&1)"
if printf '%s' "$out" | grep -q "FAILED"; then
    say "arm 2 VERDICT: a type error in $victim fails $target"
else
    say "arm 2 FAILED: mypy did NOT catch a planted error in $victim — GREEN OVER A SHORT DOMAIN"
    fail=1
fi
restore

# ⚑ ARM 3 — RESTORATION. A witness that leaves the tree dirty makes the NEXT gate's verdict a
# fact about this script.
if bazel test "$target" >/dev/null 2>&1; then
    say "arm 3 RESTORED: $dist is green again"
else
    say "arm 3 FAILED: $victim was not restored — the tree is dirty"
    fail=1
fi

[ "$fail" -eq 0 ] || { echo "domain_witness: REFUSED" >&2; exit 1; }
printf 'domain_witness: %s — domain is reachable, ranged-over, and restored\n' "$target"
