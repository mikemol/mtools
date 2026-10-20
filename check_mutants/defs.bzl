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

def mutants_sharded(name = "mutants", shards = 1, cpus = 0, cpu_budget = 0, **kwargs):
    """Declare a distribution's mutation grid as `shards` targets and a suite named `name`.

    Args:
        name: the suite's name, and the stem of the shard targets (`<name>_<i>`).
        shards: how many shards; 1 declares the single plain target.
        cpus: when above 0, each shard reserves that many CPUs with bazel's `cpu:K` tag and its
            runner starts exactly that many suites (`MUTATE_JOBS=K`), so the scheduler's count of
            a shard is the width it really uses (mtools:W980). 0 leaves both unset.
        cpu_budget: when above 0, the CPU seconds one shard may use (`MUTATE_SHARD_CPU_S`); a shard
            over it is refused by the runner with its measured CPU, so the failure threshold is CPU
            and host load cannot fail a gate (W1772). 0 declares no budget.
        **kwargs: the arguments of the `sh_test` each shard is (srcs, args, data, size, timeout).
    """
    if shards < 1:
        fail("mutants_sharded: shards must be at least 1, got %d" % shards)
    own = dict(kwargs.pop("env", {}))
    for key in ("MUTATE_SHARD", "MUTATE_JOBS"):
        if key in own:
            fail("mutants_sharded: %s is set by the macro; do not pass it in env" % key)
    if cpus < 0:
        fail("mutants_sharded: cpus must not be negative, got %d" % cpus)
    reserve = own
    if cpus:
        kwargs["tags"] = list(kwargs.get("tags", [])) + ["cpu:%d" % cpus]
        reserve = dict(own, MUTATE_JOBS = str(cpus))
    if cpu_budget < 0:
        fail("mutants_sharded: cpu_budget must not be negative, got %d" % cpu_budget)
    if cpu_budget:
        reserve = dict(reserve, MUTATE_SHARD_CPU_S = str(cpu_budget))
        # ⚑ THE WALL TIMEOUT BECOMES A BACKSTOP THAT NEVER DECIDES (W1771, operator ruling 695f3e0a
        # line 87670 plus the standing rule: bound by CPU, never a timer): the verdict is the CPU
        # budget above, so a host at load 60 slows a shard and cannot fail it. `eternal` is the
        # longest bazel allows, there only so a shard that hangs without using CPU is still ended.
        kwargs["timeout"] = "eternal"
    if shards == 1:
        native.sh_test(name = name, env = reserve, **kwargs)
        return
    names = []
    for i in range(shards):
        shard = "%s_%d" % (name, i)
        native.sh_test(
            name = shard,
            env = dict(reserve, MUTATE_SHARD = "%d/%d" % (i, shards)),
            **kwargs
        )
        names.append(shard)
    native.test_suite(name = name, tests = names)
