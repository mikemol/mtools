#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# W499: executes ci/module-gate.yml's cache-scope `case "$REF"` block, extracted from the workflow
# itself (not restated), over sample refs. Only refs/heads/stage and refs/heads/main may upload.
set -u
workflow="$1"
dollar='$'
block="$(sed -n "/^ *case \"\\${dollar}REF\" in${dollar}/,/^ *esac${dollar}/p" "$workflow")"
if [[ -z "$block" ]]; then
  echo "FAIL: no case \"\$REF\" block found in $workflow" >&2
  exit 1
fi
export CACHE_ENDPOINT=grpc://cache.example
fail=0
check() {
  local REF="$1" want="$2" cache=() got="upload"
  export REF_NAME="${1##*/}"
  eval "$block"
  if [[ ${#cache[@]} -eq 0 ]]; then
    echo "FAIL: $REF produced no cache array" >&2
    fail=1
    return
  fi
  for a in "${cache[@]}"; do
    [[ "$a" == --noremote_upload_local_results ]] && got="readonly"
  done
  if [[ "$got" != "$want" ]]; then
    echo "FAIL: $REF -> $got, want $want" >&2
    fail=1
  else
    echo "ok: $REF -> $got"
  fi
}
check refs/heads/stage upload
check refs/heads/main upload
check refs/pull/1/merge readonly
check refs/heads/feature readonly
check refs/tags/v1 readonly
exit "$fail"
