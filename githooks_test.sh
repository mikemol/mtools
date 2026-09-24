#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# Witnesses for githooks/pre-push, run against a DECOY repository in $TEST_TMPDIR — never the
# real one (a probe once pointed GIT_DIR at the real repo and made nine junk commits).
#
# Arms, each red if the hook regresses:
#   1. no local hook: the shared checks alone decide, and a clean repo pushes;
#   2. a local hook receives the same stdin BYTE FOR BYTE, and the same arguments;
#   3. a failing local hook refuses the push;
#   4. a NON-executable local hook is ignored, even one that would fail;
#   5. an operation in flight (index.lock) refuses the push BEFORE the local hook runs.
set -uo pipefail

hook="$(realpath "$1")"
work="${TEST_TMPDIR:?the decoy repository lives under TEST_TMPDIR}/decoy"
# ⚑ Scrub every GIT_* variable, so nothing inherited can point this test at another repository.
while IFS='=' read -r name _; do
  case "$name" in GIT_*) unset "$name" ;; esac
done < <(env)

fail=0
check() {
  # check <label> <expected-status> <actual-status>
  if [ "$2" != "$3" ]; then
    echo "FAIL: $1 (expected exit $2, got $3)" >&2
    fail=1
  else
    echo "ok: $1"
  fi
}

git init --quiet "$work"
mkdir "$work/.githooks"
refs=$'refs/heads/main 1111111111111111111111111111111111111111 refs/heads/main 0000000000000000000000000000000000000000\n'
seen="$TEST_TMPDIR/seen"

# 1. No local hook.
printf '%s' "$refs" | env -C "$work" "$hook" origin url
check "no local hook: a clean repo pushes" 0 "$?"

# 2. Stdin and arguments replayed.
cat >"$work/.githooks/pre-push.local" <<EOF
#!/usr/bin/env bash
cat >"$seen.stdin"
printf '%s\n' "\$@" >"$seen.args"
EOF
chmod +x "$work/.githooks/pre-push.local"
printf '%s' "$refs" | env -C "$work" "$hook" origin url
check "local hook passing: the push proceeds" 0 "$?"
if cmp -s "$seen.stdin" <(printf '%s' "$refs"); then
  echo "ok: the local hook received the ref list byte for byte"
else
  echo "FAIL: the local hook stdin differs from what git sent" >&2
  fail=1
fi
if [ "$(cat "$seen.args")" = $'origin\nurl' ]; then
  echo "ok: the local hook received the same arguments"
else
  echo "FAIL: the local hook arguments differ" >&2
  fail=1
fi

# 3. A failing local hook refuses.
printf '#!/usr/bin/env bash\nexit 7\n' >"$work/.githooks/pre-push.local"
printf '%s' "$refs" | env -C "$work" "$hook" origin url
check "a failing local hook refuses the push" 1 "$?"

# 4. A non-executable local hook is ignored.
chmod -x "$work/.githooks/pre-push.local"
printf '%s' "$refs" | env -C "$work" "$hook" origin url
check "a non-executable local hook is ignored" 0 "$?"

# 5. An operation in flight refuses first; the local hook does not run.
rm -f "$seen.stdin"
cat >"$work/.githooks/pre-push.local" <<EOF
#!/usr/bin/env bash
cat >"$seen.stdin"
EOF
chmod +x "$work/.githooks/pre-push.local"
touch "$work/.git/index.lock"
printf '%s' "$refs" | env -C "$work" "$hook" origin url
check "index.lock present: the push is refused" 1 "$?"
if [ -e "$seen.stdin" ]; then
  echo "FAIL: the local hook ran although an operation was in flight" >&2
  fail=1
else
  echo "ok: the local hook did not run while an operation was in flight"
fi

exit "$fail"
