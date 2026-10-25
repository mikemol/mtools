#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
# W1503: run the import-graph generator's --check for this distribution from a gate target. Arguments:
# the generator's executable, the distribution directory, its package. The test fails when the
# committed graph.json or dag.bzl differs by a byte from what the sources produce.
set -eu
generator="$1"
dist="$2"
package="$3"
exec "$generator" --check --dist "$dist" --package "$package"
