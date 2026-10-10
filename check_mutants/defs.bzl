# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mutants_sharded`: a distribution's mutation grid as N short targets and one name for all of them.

mtools:W971. ⚑ A TARGET THAT TIMES OUT UNDER LOAD IS SPLIT, NOT GIVEN MORE TIME OR AN `exclusive`
TAG (operator 2026-10-10). `pycodemod:mutants` took 565 s alone and timed out inside a full gate;
the grid's cost is proportional to its def-sites (about 0.6 to 0.75 s each, measured in W967), so N
shards of the runner's stable hash (`MUTATE_SHARD=i/N`, W970) are N targets of about 1/N the cost
that bazel schedules independently.

⚑ THE LABEL THE GATE RUNS KEEPS WORKING. The macro declares `<name>_0` .. `<name>_<N-1>` and a
`test_suite` called `<name>`, so `//pycodemod:mutants` still means "all of it". A `shards` of 1 is
the plain single target with no shard variable, byte for byte what the distribution had before.

⚑ NO SITE CAN BE IN NO SHARD: the runner assigns every site and every declared defect to exactly one
of N by hash, and this macro declares all N, so the union of the shards is the whole grid by
construction. Dropping a shard target from the suite is the only way to lose coverage, and the
suite lists them by the same loop that declares them.

Usage, in a distribution's BUILD.bazel, in place of its `sh_test(name = "mutants", ...)`:

    load("@mikemol_check_mutants//:defs.bzl", "mutants_sharded")
    mutants_sharded(name = "mutants", shards = 6, srcs = [...], args = [...], data = [...],
                    size = "medium", timeout = "long")
"""

def mutants_sharded(name = "mutants", shards = 1, **kwargs):
    """Declare a distribution's mutation grid as `shards` targets and a suite named `name`.

    Args:
        name: the suite's name, and the stem of the shard targets (`<name>_<i>`).
        shards: how many shards; 1 declares the single plain target.
        **kwargs: the arguments of the `sh_test` each shard is (srcs, args, data, size, timeout).
    """
    if shards < 1:
        fail("mutants_sharded: shards must be at least 1, got %d" % shards)
    if kwargs.get("env"):
        fail("mutants_sharded: env is set per shard (MUTATE_SHARD); do not pass one")
    if shards == 1:
        native.sh_test(name = name, **kwargs)
        return
    names = []
    for i in range(shards):
        shard = "%s_%d" % (name, i)
        native.sh_test(
            name = shard,
            env = {"MUTATE_SHARD": "%d/%d" % (i, shards)},
            **kwargs
        )
        names.append(shard)
    native.test_suite(name = name, tests = names)
