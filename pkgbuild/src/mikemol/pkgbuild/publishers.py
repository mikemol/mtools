# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Generate the pending-publisher worksheet for the first upload, so no field is typed (W1217).

    mikemol-wheel publishers ROOT [--index pypi|testpypi] [--html FILE]

PyPI and TestPyPI take a trusted publisher for a project that does not exist yet only through a
FORM on the account's publishing page (`/manage/account/publishing/`, a logged-in browser session;
no documented API creates or lists one, and the only token-authenticated routes in the index's
source are an echo and a project's observations). So the form cannot be scripted away, and what is
left to remove is the chance of a typo: this prints, per dist, the exact values for the five
fields, and with `--html` writes a self-contained worksheet with a copy button on every value, a
checkbox per row that the browser remembers, and a count of what is done. It is resumable (close
the page, open it tomorrow) and it changes nothing anywhere.

⚑ THE VALUES ARE READ, NOT RETYPED: the project name is each dist's own `[project].name`
normalized as an index does; the workflow file must exist under ROOT, so a renamed workflow fails
here and not at the first upload; the environment is the index's own (`pypi` or `testpypi`).

CONSUMED BY: `mikemol-wheel publishers`, the operator's registration step (W1153).
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pkgbuild import names

if TYPE_CHECKING:
    from collections.abc import Sequence

OWNER = "mikemol"
REPOSITORY = "mtools"
WORKFLOW = "publish.yml"
INDEXES = {
    "pypi": ("pypi", "https://pypi.org/manage/account/publishing/"),
    "testpypi": ("testpypi", "https://test.pypi.org/manage/account/publishing/"),
}
FIELDS = ("PyPI Project Name", "Owner", "Repository name", "Workflow name", "Environment name")
USAGE = 2
SYNOPSIS = "usage: mikemol-wheel publishers ROOT [--index pypi|testpypi] [--html FILE]\n"
STYLE = (
    "body{font:15px system-ui;margin:1.5rem}table{border-collapse:collapse}"
    "td,th{border:1px solid #888;padding:.3rem .5rem;text-align:left}button{margin-left:.4rem}"
)
SCRIPT = (
    "const boxes=[...document.querySelectorAll('input[data-key]')];"
    "const show=()=>{document.getElementById('count').textContent="
    "boxes.filter(b=>b.checked).length+' of '+boxes.length+' done'};"
    "boxes.forEach(b=>{b.checked=localStorage.getItem(b.dataset.key)==='1';"
    "b.addEventListener('change',()=>{"
    "localStorage.setItem(b.dataset.key,b.checked?'1':'0');show()})});"
    "document.querySelectorAll('button[data-copy]').forEach(b=>"
    "b.addEventListener('click',()=>navigator.clipboard.writeText(b.dataset.copy)));show();"
)
Row = dict[str, str]


def rows_of(root: Path, index: str) -> list[Row]:
    """Read one row of field values per dist.

    Returns:
        the rows, in dist order, each mapping the form's field labels to their values.

    """
    environment, _ = INDEXES[index]
    found: list[Row] = []
    for pyproject in sorted(root.glob("*/pyproject.toml")):
        dist = pyproject.parent
        declared = names.project_name(dist)
        if dist.is_symlink() or declared is None:
            continue
        values = (names.normalized(declared), OWNER, REPOSITORY, WORKFLOW, environment)
        found.append(dict(zip(FIELDS, values, strict=True)))
    return found


def _cell(label: str, value: str) -> str:
    safe = html.escape(value, quote=True)
    return (
        f'<td><code>{safe}</code><button type="button" data-copy="{safe}" '
        f'aria-label="copy {html.escape(label)}">copy</button></td>'
    )


def _tick(index: str, project: str) -> str:
    key = html.escape(f"{index}:{project}", quote=True)
    label = html.escape(f"done: {project}", quote=True)
    return f'<td><input type="checkbox" data-key="{key}" aria-label="{label}"></td>'


def worksheet(rows: Sequence[Row], index: str) -> str:
    """Render the worksheet as one self-contained HTML page.

    Returns:
        the page text: a table with a copy button per value and a remembered checkbox per row.

    """
    _, form = INDEXES[index]
    head = "".join(f"<th>{html.escape(f)}</th>" for f in FIELDS)
    body = "".join(
        "<tr>" + "".join(_cell(f, row[f]) for f in FIELDS) + _tick(index, row[FIELDS[0]]) + "</tr>"
        for row in rows
    )
    link = html.escape(form, quote=True)
    return (
        "<!doctype html><html lang=en><meta charset=utf-8>"
        f"<title>Pending publishers on {html.escape(index)}</title><style>{STYLE}</style>"
        f"<h1>Pending publishers on {html.escape(index)}</h1>"
        f'<p>Open <a href="{link}">{link}</a>, choose GitHub, and for each row paste the five '
        "values, press Add, then tick the row. Ticks are remembered by this browser; close the "
        'page and come back. <b id="count"></b></p>'
        f"<table><tr>{head}<th>done</th></tr>{body}</table><script>{SCRIPT}</script></html>"
    )


def _options(words: list[str]) -> dict[str, str] | None:
    """Take `--index` and `--html` and their values out of `words`.

    Returns:
        the options given, or None when one has no value.

    """
    found: dict[str, str] = {}
    for flag in ("--index", "--html"):
        if flag in words:
            place = words.index(flag)
            if place + 1 >= len(words):
                return None
            found[flag] = words[place + 1]
            del words[place : place + 2]
    return found


def run(args: Sequence[str]) -> int:
    """Run `ROOT [--index NAME] [--html FILE]`: one JSON line per dist, and the worksheet if asked.

    Returns:
        0, or 2 for a usage error, a missing workflow file or no dist found.

    """
    words = list(args)
    options = _options(words)
    index = (options or {}).get("--index", "pypi")
    if options is None or len(words) != 1 or index not in INDEXES:
        sys.stderr.write(SYNOPSIS)
        return USAGE
    root = Path(words[0])
    if not (root / ".github" / "workflows" / WORKFLOW).is_file():
        sys.stderr.write(f"publishers: {root}/.github/workflows/{WORKFLOW} does not exist\n")
        return USAGE
    rows = rows_of(root, index)
    if not rows:
        sys.stderr.write("publishers: no dist found\n")
        return USAGE
    sys.stdout.writelines(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    if "--html" in options:
        Path(options["--html"]).write_text(worksheet(rows, index), encoding="utf-8")
    return 0
