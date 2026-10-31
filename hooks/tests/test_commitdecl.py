# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The commit declaration is read whole, an absent file is empty and a wrong one is refused (W2130).

⚑ THE CONTROLS: an absent file and `{}` both read as an empty declaration, and each wrong shape
(not JSON, not an object, `paths` not a list, a non-string path, `pre_steps` not a list, a step
that is not a list of strings) raises the named error instead of reading as nothing.
"""

import json
from pathlib import Path

import pytest

from mikemol.hooks import commitdecl


def _declare(root: Path, text: str) -> None:
    (root / ".claude").mkdir(exist_ok=True)
    (root / commitdecl.NAME).write_text(text, encoding="utf-8")


def test_a_declaration_is_read_with_its_paths_and_its_steps(tmp_path: Path) -> None:
    """Both fields come back as tuples, steps as argv tuples."""
    doc = {"paths": ["a/b.py", "c.txt"], "pre_steps": [["tool", "--flag"], ["other"]]}
    _declare(tmp_path, json.dumps(doc))
    assert commitdecl.read(tmp_path) == commitdecl.Declaration(
        ("a/b.py", "c.txt"), (("tool", "--flag"), ("other",))
    )


def test_an_absent_file_and_an_empty_object_read_as_the_empty_declaration(tmp_path: Path) -> None:
    """Nothing declared is not an error."""
    assert commitdecl.read(tmp_path) == commitdecl.Declaration()
    _declare(tmp_path, "{}")
    assert commitdecl.read(tmp_path) == commitdecl.Declaration()


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "[]",
        '{"paths": "a.py"}',
        '{"paths": ["a.py", 3]}',
        '{"pre_steps": "tool"}',
        '{"pre_steps": ["tool"]}',
        '{"pre_steps": [["tool", 1]]}',
    ],
)
def test_each_wrong_shape_is_refused_by_name(tmp_path: Path, text: str) -> None:
    """A file that is there and wrong raises, it never reads as empty."""
    _declare(tmp_path, text)
    with pytest.raises(commitdecl.DeclarationError):
        commitdecl.read(tmp_path)
