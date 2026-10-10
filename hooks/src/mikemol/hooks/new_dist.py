# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The pure core of `mikemol-new-dist`: a new distribution as text-to-text functions (mtools:W944).

A distribution is a directory of generic files plus four edits elsewhere (three in `MODULE.bazel`,
one in `INSTALL.md`), measured by `git ls-files pathwalk` and `git grep pathwalk` (design:
`.claude/design/W943-new-dist.md`). Nothing here touches the disk, runs `uv` or reads a repository:
the shell (W945) reads the template's files and writes what these return, so every rule below is
tested on text fixtures.

⚑ THE TEMPLATE'S NAME IS REPLACED EVERYWHERE (paper.toml, the one place it is upper-cased, is
generated rather than renamed), and what the template says ABOUT ITSELF is cut rather than
renamed: its description, its keywords, the
comment block about its birth, its per-module lint exemptions and its defect declarations. A
renamed paragraph about someone else's history is a false statement in the new directory.

⚑ A BAD INPUT IS REFUSED BY NAME, NOT REPAIRED: a name that is not `[a-z][a-z0-9]*`, a description
that would break out of a TOML string, an anchor that is not found exactly once. A generator that
guesses writes a plausible-looking file the gate then rejects somewhere else.

CONSUMED BY: the `mikemol-new-dist` console script (W945).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

TEMPLATE = "pathwalk"
_NAME = re.compile(r"[a-z][a-z0-9]*")
_SPDX = "# SPDX-License-Identifier: Apache-2.0\n# Copyright (c) 2026 Mike Mol\n"
_IGNORES = "[tool.ruff.lint.per-file-ignores]"
_FILES = (
    "BUILD.bazel",
    "paper.toml",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
)
FILES = _FILES
_MUTANTS_HEADER = (
    f"{_SPDX}#\n"
    "# The defect classes this distribution DECLARES (mtools:W629), planted one at a time by the\n"
    "# `:mutants` runner: <module>|<name>|<pattern>|<replacement>|<scope>. A line that stops\n"
    "# matching is a STALE declaration and fails the grid as UNAPPLIED.\n"
)


def check_name(name: str) -> None:
    """Refuse a distribution name that is not a lowercase word.

    Raises:
        ValueError: when `name` is not `[a-z][a-z0-9]*`.

    """
    if _NAME.fullmatch(name) is None:
        msg = f"distribution name {name!r} must match [a-z][a-z0-9]*"
        raise ValueError(msg)


def check_description(description: str) -> None:
    """Refuse a description that is empty or would break out of a TOML string.

    Raises:
        ValueError: when it is blank, or holds a quote, a backslash or a line break.

    """
    if not description.strip() or any(ch in description for ch in '"\\\n'):
        msg = "description must be one non-empty line with no quote or backslash"
        raise ValueError(msg)


def rename(text: str, old: str, new: str) -> str:
    """Replace the template's name by the new one.

    Returns:
        the text with every occurrence replaced.

    """
    return text.replace(old, new)


def _build(text: str, name: str, template: str) -> str:
    """Make BUILD.bazel: from its first `load(` on, renamed, under a fresh header.

    Returns:
        the new file's text.

    Raises:
        ValueError: when the template's BUILD.bazel has no `load(` line.

    """
    cut = text.find("load(")
    if cut < 0:
        msg = "the template's BUILD.bazel has no load( line"
        raise ValueError(msg)
    header = (
        f"{_SPDX}\n# ⚑ SCAFFOLDED by mikemol-new-dist (W943) from //{template}; the rationale for\n"
        f"# each shape lives there. `@{name}_dev` is declared in MODULE.bazel beside it.\n"
    )
    return rename(header + text[cut:], template, name)


def _pyproject(text: str, name: str, description: str, template: str) -> str:
    """Make pyproject.toml: the template's, with its own history and exemptions cut.

    Returns:
        the new file's text, ending in a per-file-ignores table naming only the smoke test.

    """
    head = text.partition(_IGNORES)[0]
    head = re.sub(r"(\[project\]\n)(?:#.*\n)+(name = )", r"\1\2", head)
    head = re.sub(r'(?m)^description = ".*"$', f'description = "{description}"', head)
    head = re.sub(r"(?m)^keywords = \[.*\]$", f'keywords = ["{name}"]', head)
    tail = f'{_IGNORES}\n"tests/test_smoke.py" = ["assert"]\n'
    return rename(head + tail, template, name)


def _requirements(text: str, name: str, template: str) -> str:
    """Make a requirements file: renamed, with `via mikemol-<dist>` attributions retargeted.

    Returns:
        the new file's text.

    """
    attribution = re.compile(r"mikemol-[a-z0-9]+ \(pyproject\.toml:dev\)")
    return rename(attribution.sub(f"mikemol-{name} (pyproject.toml:dev)", text), template, name)


def _paper(name: str, description: str) -> str:
    """Make paper.toml for the new distribution's warrants.

    Returns:
        the file's text.

    """
    return (
        f'[paper]\ntitle = "mikemol.{name}: {description}"\n'
        f'subtitle = "The witnesses behind mikemol.{name}."\nwarrants = ["warrants.bib"]\n'
        f'rubric = "rubric.tsv"\nout = "{name.upper()}.md"\n'
        "numbered = false\nreferences = false\n\n"
        '[checks.cmd]\ncmd = "{target}"\n'
    )


def _smoke(name: str) -> str:
    """Make the one test every scaffold carries, so a suite is never empty.

    Returns:
        the test module's text.

    """
    return (
        f'{_SPDX}"""The scaffold\'s one witness: the package imports and says what it is."""\n\n'
        f"from __future__ import annotations\n\nimport mikemol.{name} as package\n\n\n"
        "def test_the_package_imports_and_carries_its_docstring() -> None:\n"
        '    """The scaffold compiles, imports and documents itself."""\n'
        "    assert package.__doc__ is not None\n"
    )


def skeleton(
    name: str, description: str, template: Mapping[str, str], template_name: str = TEMPLATE
) -> dict[str, str]:
    """Build every file of a new distribution, as `{path under <name>/: text}`.

    `template` holds the template's BUILD.bazel, paper.toml, pyproject.toml, requirements.txt and
    requirements-dev.txt. The uv.lock is NOT here: it embeds the project's name and is generated.

    Returns:
        the relative path of each file and its text.

    Raises:
        ValueError: on a bad name or description, or a template missing one of its files.

    """
    check_name(name)
    check_description(description)
    missing = [f for f in _FILES if f not in template]
    if missing:
        msg = f"the template is missing {missing}"
        raise ValueError(msg)
    return {
        "BUILD.bazel": _build(template["BUILD.bazel"], name, template_name),
        "pyproject.toml": _pyproject(template["pyproject.toml"], name, description, template_name),
        "requirements.txt": _requirements(template["requirements.txt"], name, template_name),
        "requirements-dev.txt": _requirements(
            template["requirements-dev.txt"], name, template_name
        ),
        "paper.toml": _paper(name, description),
        "README.md": (
            "<!-- SPDX-License-Identifier: Apache-2.0 -->\n<!-- Copyright (c) 2026 Mike Mol -->\n\n"
            f"# mikemol-{name}\n\n{description}\n"
        ),
        "mutants.regex": _MUTANTS_HEADER,
        "rubric.tsv": (
            f"# rubric.tsv — the sections of the {name} warrant set, one per test module,\n"
            "# in document order.\n# key <TAB> heading title\n"
        ),
        "warrants.bib": "",
        "ratchet-preview.txt": "",
        f"src/mikemol/{name}/__init__.py": f'{_SPDX}"""mikemol.{name}: {description}"""\n',
        f"src/mikemol/{name}/py.typed": "",
        "tests/test_smoke.py": _smoke(name),
    }


def _once(text: str, anchor: str) -> int:
    """Find an anchor that must occur exactly once.

    Returns:
        the index just past the anchor.

    Raises:
        ValueError: when the anchor is absent or repeated.

    """
    count = text.count(anchor)
    if count != 1:
        msg = f"expected exactly one {anchor!r} in the file, found {count}"
        raise ValueError(msg)
    return text.index(anchor) + len(anchor)


def _insert_after(text: str, anchor: str, addition: str) -> str:
    """Insert `addition` immediately after the one occurrence of `anchor`.

    Returns:
        the text with the addition in place.

    """
    end = _once(text, anchor)
    return text[:end] + addition + text[end:]


def _note(name: str) -> str:
    """Say in MODULE.bazel where a scaffolded hub came from.

    Returns:
        a comment for the hub.

    """
    return (
        f"# ⚑ `mikemol-{name}` — scaffolded by mikemol-new-dist (W943). Empty shipping hub until\n"
        "# it declares a dependency.\n"
    )


def module_edit(text: str, name: str, template: str = TEMPLATE) -> str:
    """Add a new distribution's pip hubs and `use_repo` names to MODULE.bazel.

    Each addition is a copy of the template's own block, placed just after it.

    Returns:
        the edited text.

    Raises:
        ValueError: on a bad name, a name already present, or an anchor not found once.

    """
    check_name(name)
    if f'"{name}_deps"' in text:
        msg = f"MODULE.bazel already declares {name}_deps"
        raise ValueError(msg)
    deps = (
        f'pip.parse(\n    hub_name = "{template}_deps",\n    python_version = "3.13",\n'
        f'    requirements_lock = "//{template}:requirements.txt",\n)\n'
    )
    dev = (
        f'pip.parse(\n    hub_name = "{template}_dev",\n    python_version = "3.13",\n'
        f'    uv_lock = "//{template}:uv.lock",\n)\n'
    )
    text = _insert_after(text, deps, "\n" + _note(name) + rename(deps, template, name))
    text = _insert_after(text, dev, rename(dev, template, name))
    for hub in (f"{template}_deps", f"{template}_dev"):
        text = _insert_after(text, f'    "{hub}",\n', f'    "{hub.replace(template, name)}",\n')
    return text


def install_edit(text: str, name: str, summary: str) -> str:
    """Add the distribution to INSTALL.md: an alphabetical entry and the count bumped.

    Returns:
        the edited text.

    Raises:
        ValueError: when the count sentence or the entry list is not found, or the name is present.

    """
    check_name(name)
    check_description(summary)
    if f"- `{name}` " in text:
        msg = f"INSTALL.md already lists {name}"
        raise ValueError(msg)
    count = re.search(r"There are (\d+) of them", text)
    if count is None:
        msg = "INSTALL.md has no 'There are N of them' sentence"
        raise ValueError(msg)
    text = text[: count.start(1)] + str(int(count.group(1)) + 1) + text[count.end(1) :]
    entry = f"- `{name}` (`mikemol-{name}`): {summary} A library, no scripts.\n"
    found = re.finditer(r"(?m)^- `([a-z0-9]+)` ", text)
    keys = [(m.start(), str(m.group(1))) for m in found]
    if not keys:
        msg = "INSTALL.md lists no distributions"
        raise ValueError(msg)
    before = next((pos for pos, key in keys if key > name), None)
    if before is not None:
        return text[:before] + entry + text[before:]
    blank = text.find("\n\n", keys[-1][0])
    end = len(text) if blank < 0 else blank + 1
    return text[:end] + entry + text[end:]
