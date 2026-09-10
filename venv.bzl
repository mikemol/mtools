# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A distribution's `.venv`, built as an artifact rather than left as host state.

⚑⚑⚑ THE OPERATOR DIRECTION THIS ANSWERS: *"All projects in this repo should be constructing
their .venv the same way -- as a build artifact. This should be a trivially-templatizable
thing."* Four distributions, one macro, one call each.

⚑⚑ AND IT DUPLICATES CONSTRUCTION rules_python ALREADY DOES, KNOWINGLY. `venv_runfiles.bzl`
builds `_<target>.venv/bin/python3` for every `py_test`/`py_binary` — that is what
`sys.executable` names inside an action, measured. The operator was shown this and ruled for a
whole-distribution venv anyway, because a PER-TARGET venv cannot be ACTIVATED, and this
repository has three non-bazel consumers that reach `<dist>/.venv/bin/...`: `.githooks/pre-commit`
(13 call sites), `preflight.sh` (7), and the interactive dev loop. Those are the users; the
duplication is the price.

⚑ WHAT IS NOT DUPLICATED: no resolver, no installer, no network. The wheels arrive already
unpacked through `pip.parse`, which `MODULE.bazel` declares. This macro only ARRANGES staged
files into the layout a venv has.
"""

# ⚑⚑ MEASURED, NOT ASSUMED: `@<hub>//<pkg>:extracted_whl_files` is a plain `filegroup` carrying
# individual `File`s (checked with `cquery --output=files`, and its providers are
# DefaultInfo/FileProvider — no tree artifact, no custom provider to unwrap). Every path inside it
# is prefixed `site-packages/`, which is what makes the destination computable by stripping.
# ⚑ THE ADJACENT `whl_filegroup` RULE IS A DIFFERENT TARGET and does use `declare_directory`; its
# docstring points AT `extracted_whl_files` as a separate thing. Reading one for the other would
# have produced a rule built on a tree artifact that is not there.
_SITE = "site-packages/"

def _venv_impl(ctx):
    outs = []

    # ⚑⚑⚑ THE INTERPRETER LINK MUST BE RELATIVE, AND THIS IS THE WHOLE BUILD-ARTIFACT PROPERTY.
    # MEASURED, both arms: a venv whose `bin/python3` is an ABSOLUTE symlink stops working the
    # moment the interpreter moves, while `pyvenv.cfg`'s `home` is INERT -- rewriting it to
    # `/nonexistent/nowhere` changed NOTHING, so an earlier probe that "confirmed" relocatability
    # by editing `home` had measured nothing at all. The symlink is the real dependency.
    # ⚑ An artifact that is only valid at the path it was built at is host state with a build
    # step in front of it.
    interpreter = ctx.toolchains["@rules_python//python:toolchain_type"].py3_runtime.interpreter

    # bin/python3 -> the staged toolchain, by a path relative to the link's own directory.
    python3 = ctx.actions.declare_symlink(ctx.attr.name + "/bin/python3")

    # ⚑⚑⚑ `path`, NOT `short_path`, AND THE FIRST DRAFT USED `short_path` AND BUILT A BROKEN LINK.
    # Both are "the file's path" and they are DIFFERENT VIEWS. Measured, by printing all four
    # during a build rather than reasoning about which to use:
    #
    #     link.short_path   = hooks/.venv/bin/python3
    #     link.path         = bazel-out/k8-fastbuild/bin/hooks/.venv/bin/python3
    #     interp.short_path = ../rules_python++python+.../bin/python3      <- LEADING ../
    #     interp.path       = external/rules_python++python+.../bin/python3
    #
    # ⚑⚑ AN EXTERNAL FILE'S `short_path` BEGINS `../`, because runfiles put other repositories
    # BESIDE the main one. Walking a common prefix across a `short_path` pair therefore compares a
    # workspace-relative path against an escape sequence, and the `../` counted as an ordinary
    # segment. The link that produced was well-formed, pointed into `bazel-out/`, and named
    # nothing — the same shape as the sys.path finding at 8221131, one layer down: a path that
    # exists as a string and not as a file. `path` is execroot-relative for BOTH, so the walk is
    # over one coordinate system.
    ctx.actions.symlink(
        output = python3,
        target_path = _relative_path(python3.path, interpreter.path),
    )
    outs.append(python3)

    # ⚑ `pyvenv.cfg` IS WRITTEN BECAUSE A VENV IS DEFINED BY ITS PRESENCE, not because its
    # contents are consulted. `home` is recorded for a human reader; the measurement above says
    # Python does not resolve through it. Stating that here so the next reader does not "fix" a
    # value nothing reads, or trust it to relocate anything.
    cfg = ctx.actions.declare_file(ctx.attr.name + "/pyvenv.cfg")
    ctx.actions.write(
        output = cfg,
        content = "home = ../bin\ninclude-system-site-packages = false\nversion = {}\n".format(
            ctx.attr.python_version,
        ),
    )
    outs.append(cfg)

    # ⚑⚑ THE CLOSURE COMES FROM `deps`, WHICH COMES FROM THE GRAPH -- NOT FROM A DIRECTORY SCAN.
    # MEASURED WHY: scanning `external/rules_python++pip+hooks_*` finds 39 directories, of which 2
    # have no `site-packages` at all (the hub aliases `hooks_deps`/`hooks_dev` themselves) and the
    # rest are DUPLICATE PAIRS -- a short alias and a long platform-tagged name resolving to the
    # same wheel. A hand-assembled probe survived that only because duplicate basenames collide
    # harmlessly. A rule must not rest on a coincidence.
    site = ctx.attr.name + "/lib/python" + ctx.attr.python_version_short + "/site-packages"
    seen = {}
    for dep in ctx.attr.deps:
        for f in dep[DefaultInfo].files.to_list():
            # ⚑ `path` HERE TOO, for one coordinate system throughout — though this use only
            # needs the `site-packages/` marker and its tail, which both views agree on.
            idx = f.path.find(_SITE)
            if idx < 0:
                continue  # the .whl itself, metadata.json, MODULE.bazel -- not venv content
            rel = f.path[idx + len(_SITE):]
            if rel in seen:
                continue  # the duplicate-hub pairs measured above resolve to identical files
            seen[rel] = True
            out = ctx.actions.declare_file(site + "/" + rel)
            ctx.actions.symlink(output = out, target_file = f)
            outs.append(out)

    # ⚑⚑⚑ THE DISTRIBUTION'S OWN SOURCE IS NOT A DEPENDENCY AND MUST STILL BE PRESENT. Measured:
    # the venv built from `deps` alone runs pytest and then dies on
    # `ModuleNotFoundError: No module named 'mikemol'` — CORRECT behaviour, not a defect. A venv
    # holds a project's dependencies; the project itself arrives by an EDITABLE INSTALL, which is
    # exactly the host-state step this rule exists to remove.
    # ⚑⚑ SO IT IS DECLARED RATHER THAN INFERRED. `srcs` names the package roots to expose, and a
    # distribution that names none gets a dependencies-only venv — which is a legitimate thing to
    # want and should not be silently "fixed" by a rule guessing at `src/`.
    for f in ctx.files.srcs:
        idx = f.path.find(ctx.attr.src_root + "/")
        if idx < 0:
            continue
        rel = f.path[idx + len(ctx.attr.src_root) + 1:]
        out = ctx.actions.declare_file(site + "/" + rel)
        ctx.actions.symlink(output = out, target_file = f)
        outs.append(out)

    return [DefaultInfo(files = depset(outs), runfiles = ctx.runfiles(files = outs))]

def _relative_path(from_file, to_file):
    """Path from `from_file`'s DIRECTORY to `to_file`, as `../` segments plus a tail."""
    from_parts = from_file.split("/")[:-1]  # drop the filename: we walk from its directory
    to_parts = to_file.split("/")
    common = 0
    for i in range(min(len(from_parts), len(to_parts) - 1)):
        if from_parts[i] != to_parts[i]:
            break
        common += 1
    return "/".join([".."] * (len(from_parts) - common) + to_parts[common:])

venv = rule(
    implementation = _venv_impl,
    doc = "Assembles a relocatable venv from wheels bazel has already staged.",
    attrs = {
        "deps": attr.label_list(
            doc = "`@<hub>//<pkg>:extracted_whl_files` targets to place in site-packages.",
            allow_files = True,
        ),
        "python_version": attr.string(mandatory = True, doc = "Full version, e.g. 3.13.13."),
        "python_version_short": attr.string(mandatory = True, doc = "Major.minor, e.g. 3.13."),
        "src_root": attr.string(
            default = "src",
            doc = "Directory under which `srcs` paths become site-packages-relative.",
        ),
        "srcs": attr.label_list(
            allow_files = True,
            doc = "The distribution's OWN sources, standing in for an editable install.",
        ),
    },
    toolchains = ["@rules_python//python:toolchain_type"],
)

def venv_from_hub(name, hub_requirements, python_version, python_version_short, srcs = None, src_root = "src"):
    """The templatizable form: one call per distribution, population taken from the hub.

    ⚑⚑⚑ THIS IS WHERE "TRIVIALLY TEMPLATIZABLE" LIVES. A distribution says its name, its hub's
    generated `all_requirements`, and its Python version. Everything else is derived.

    ⚑⚑ THE `:pkg` -> `:extracted_whl_files` REWRITE IS HERE RATHER THAN AT EACH CALL SITE, because
    `pip.parse` generates accessors for `pkg`/`whl`/`data`/`dist_info` and NONE for the extracted
    files -- measured by reading the generated `requirements.bzl`, after a first draft guessed a
    `_extracted` suffix that names nothing. Doing the rewrite once means a wrong guess is wrong in
    one place, not four.

    Args:
        name: the venv directory, conventionally `.venv`.
        hub_requirements: the hub's generated `all_requirements` list.
        python_version: full version string, e.g. `3.13.13`.
        python_version_short: major.minor, e.g. `3.13`.
        srcs: the distribution's own sources, standing in for an editable install.
        src_root: directory under which `srcs` paths become site-packages-relative.
    """
    venv(
        name = name,
        deps = [r.removesuffix(":pkg") + ":extracted_whl_files" for r in hub_requirements],
        python_version = python_version,
        python_version_short = python_version_short,
        src_root = src_root,
        srcs = srcs or [],
    )
