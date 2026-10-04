# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Which relations a SQL string reads and writes, and where a name is used AS a relation.

Cleanroomed from substrate's `scratch/_pycodemod_sql.py` (`sql_rel_roles`, `sql_relnames`,
`sql_kind`, `sql_rw`, `relname_sites`; W594). A substring match on a short relation name is not a
census (`node` finds `node_child`, `obs_node`, `_node`); the question is a GRAMMAR POSITION, so the
SQL is lexed and the name is read where a relation may stand.

⚑⚑ THE ROLE IS CARRIED WITH THE NAME, NOT RECOVERED LATER. `DELETE FROM t WHERE EXISTS (SELECT 1
FROM s)` and `INSERT INTO t SELECT … WHERE NOT EXISTS (SELECT 1 FROM t …)` name a relation twice
with opposite meanings; the grammar position that finds the name is the only thing that knows which
way. `sql_relnames` and `sql_rw` are projections of `sql_rel_roles`, so they cannot disagree.

⚑ STATED BOUNDS, NOT REPAIRED HERE:
  * a keyword that ends a relation list is a roster (`_END`); a relation genuinely NAMED `set` or
    `values` reads as a terminator.
  * a CTE is a name bound by the statement, not a relation the store holds, and is excluded.
  * a table FUNCTION (`FROM generate_series(…)`) names no stored relation; the trailing `(` is what
    tells it from a column list (`INSERT INTO t (a, b)`), which is why the write positions never
    treat `(` as a call.
  * `relname_sites` sees `ast.Constant` strings only (not f-strings), and decides what is SQL with
    SQLite's parser alone; a statement only postgres accepts is not seen. The origin also asked a
    postgres probe; that probe is a connection to a store and is not a pure function of the string,
    so it did not move.
"""

from __future__ import annotations

import re
import sqlite3
from typing import TYPE_CHECKING, NamedTuple

from mikemol.pycodemod.strings import Found, literal_sites

if TYPE_CHECKING:
    from collections.abc import Sequence

type Tok = tuple[str, str]
type Roles = set[tuple[str, str]]

_TOKEN = re.compile(
    r"""(?P<ws>\s+)
      | (?P<lc>--[^\n]*)
      | (?P<bc>/\*.*?\*/)
      | (?P<str>'(?:[^']|'')*')
      | (?P<qid>"(?:[^"]|"")*")
      | (?P<id>[A-Za-z_][A-Za-z_0-9$]*)
      | (?P<num>\d+(?:\.\d+)?)
      | (?P<op>.)""",
    re.VERBOSE | re.DOTALL,
)

_END = frozenset(
    {
        *("where", "group", "order", "having", "limit", "offset", "fetch", "window", "union"),
        *("intersect", "except", "returning", "set", "values", "on", "using", "join", "left"),
        *("right", "inner", "outer", "full", "cross", "natural", "with", "select", "from"),
        *("into", "as", "and", "or", "not", "when", "then", "else", "end", "for", "do"),
        *("conflict", "nothing", "update", "delete", "insert", "create", "drop", "alter"),
        *("truncate", "table", "view", "index", "if", "exists", "distinct", "all", "by"),
        *("asc", "desc", "ordinality", "recursive", "primary", "key", "constraint", "unique"),
        *("default", "null", "case", "is", "in", "like", "between", "over", "partition"),
        *("filter", "tablesample"),
    }
)
_QUERY_HEADS = frozenset({"select", "with", "values", "table"})
_KIND_HEADS = frozenset(
    {
        "delete",
        "insert",
        "update",
        "replace",
        "merge",
        "create",
        "drop",
        "alter",
        "truncate",
        "select",
        "values",
    }
)
_DDL_LEADERS = frozenset(
    {
        "create",
        "drop",
        "alter",
        "truncate",
        "replace",
        "materialized",
        "temp",
        "temporary",
        "unlogged",
        "or",
    }
)
_SQL_HEADS = frozenset(
    {"select", "insert", "update", "delete", "create", "drop", "alter", "with", "pragma", "replace"}
)
_PLACEHOLDER = re.compile(r"%\(\w+\)s|%[sdifr]|(?<![\w$]):[a-z_]\w*", re.IGNORECASE)


def _tokens(sql: str) -> list[Tok]:
    """Return the SQL lexed to (kind, text), whitespace and comments dropped.

    Returns:
        the tokens.

    """
    return [
        (m.lastgroup or "op", m.group())
        for m in _TOKEN.finditer(sql)
        if m.lastgroup not in {"ws", "lc", "bc"}
    ]


def _ident(text: str) -> str:
    return text[1:-1].replace('""', '"') if text.startswith('"') else text


def _match(toks: list[Tok], start: int, hi: int) -> int:
    """Return the index of the `)` matching the `(` at `start`, or `hi` if unbalanced.

    Returns:
        the closing index.

    """
    depth = 0
    for i in range(start, hi):
        if toks[i][1] == "(":
            depth += 1
        elif toks[i][1] == ")":
            depth -= 1
            if depth == 0:
                return i
    return hi


def _is_name(tok: Tok) -> bool:
    return tok[0] in {"id", "qid"}


def _skip_alias(toks: list[Tok], i: int, hi: int) -> int:
    """Return the index past an `AS x` or bare `x` alias and any `(col, …)` alias list.

    Returns:
        the index after the alias.

    """
    if i < hi and toks[i][0] == "id" and toks[i][1].lower() == "as":
        i += 1
        if i < hi and _is_name(toks[i]):
            i += 1
    elif i < hi and _is_name(toks[i]) and (toks[i][0] == "qid" or toks[i][1].lower() not in _END):
        i += 1
    if i < hi and toks[i][1] == "(":
        i = _match(toks, i, hi) + 1
    return i


def _relation_list(toks: list[Tok], i: int, hi: int, mode: str, role: str) -> tuple[int, Roles]:
    """Return (next index, {(name, role)}) for the relation list starting at `i`.

    `mode` is the grammar position: `from` (a comma list), `join` (one relation), or `write`
    (one relation, as after INSERT INTO / UPDATE / CREATE TABLE).

    ⚑⚑ THE `write` MODE IS WHY `INSERT INTO terms (a, b)` FINDS `terms`: a `(` after a name is a
    TABLE FUNCTION in a FROM/JOIN position and a COLUMN LIST after INSERT INTO / UPDATE / CREATE.
    ⚑ A DERIVED TABLE RECURSES rather than being skipped; skipping it reports
    `SELECT count(*) FROM (SELECT … FROM t) d` as touching no relation.

    Returns:
        the index after the list, and the (name, role) pairs found in it.

    """
    out: Roles = set()
    while i < hi:
        while i < hi and toks[i][0] == "id" and toks[i][1].lower() in {"only", "lateral"}:
            i += 1
        if i >= hi:
            break
        kind, text = toks[i]
        if text == "(":
            end = _match(toks, i, hi)
            nxt = toks[i + 1][1].lower() if i + 1 < end else ""
            out |= _walk(toks, i + 1, end, qscope=nxt in _QUERY_HEADS)
            i = _skip_alias(toks, end + 1, hi)
        elif kind in {"id", "qid"}:
            if kind == "id" and text.lower() in _END:
                break
            name = _ident(text)
            i += 1
            while i + 1 < hi and toks[i][1] == "." and _is_name(toks[i + 1]):
                name = _ident(toks[i + 1][1])
                i += 2
            if mode != "write" and i < hi and toks[i][1] == "(":
                i = _match(toks, i, hi) + 1
            else:
                out.add((name.lower(), role))
            i = _skip_alias(toks, i, hi)
        else:
            break
        if mode != "from" or i >= hi or toks[i][1] != ",":
            break
        i += 1
    return i, out


def _previous_word(toks: list[Tok], i: int, lo: int) -> str:
    """Return the nearest identifier among the two tokens before `i`, lowercased, or "".

    Returns:
        the word, or the empty string.

    """
    for j in range(i - 1, max(lo, i - 3) - 1, -1):
        if toks[j][0] == "id":
            return toks[j][1].lower()
    return ""


def _walk(toks: list[Tok], lo: int, hi: int, *, qscope: bool) -> Roles:
    """Return {(name, role)} referenced in `toks[lo:hi]`; role `r` read, `w` written.

    ⚑ `DELETE`'S TARGET SITS AFTER `FROM`, the token that introduces every read; the token BEFORE
    it separates them. ⚑ `qscope` IS WHY `EXTRACT(EPOCH FROM ts)` NAMES NO RELATION: a paren opens a
    query scope only if its first token is select/with/values/table, and recursion happens either
    way so a subquery inside an expression re-enters query scope on its own paren.
    ⚑ `IS [NOT] DISTINCT FROM` is not a relation introducer; `distinct` before `FROM` is the
    discriminator, and `SELECT DISTINCT x FROM t` is excluded from it by sitting before `x`.

    Returns:
        the (name, role) pairs.

    """
    out: Roles = set()
    i = lo
    while i < hi:
        kind, text = toks[i]
        if text == "(":
            end = _match(toks, i, hi)
            nxt = toks[i + 1][1].lower() if i + 1 < end else ""
            out |= _walk(toks, i + 1, end, qscope=nxt in _QUERY_HEADS)
            i = end + 1
            continue
        if kind != "id" or not qscope:
            i += 1
            continue
        low = text.lower()
        prev = _previous_word(toks, i, lo)
        if low in {"from", "join"} and not (low == "from" and prev == "distinct"):
            role = "w" if low == "from" and prev == "delete" else "r"
            i, got = _relation_list(toks, i + 1, hi, low, role)
            out |= got
        elif low == "update" or (low == "into" and prev in {"insert", "replace"}):
            i, got = _relation_list(toks, i + 1, hi, "write", "w")
            out |= got
        elif low in {"table", "view"} and prev in _DDL_LEADERS:
            j = i + 1
            while j < hi and toks[j][0] == "id" and toks[j][1].lower() in {"if", "not", "exists"}:
                j += 1
            i, got = _relation_list(toks, j, hi, "write", "w")
            out |= got
        else:
            i += 1
    return out


def _cte_names(toks: list[Tok]) -> set[str]:
    """Return the names bound by `X AS (` and `X (cols) AS (`, the only CTE signature.

    Returns:
        the lowercased CTE names.

    """
    n = len(toks)
    ctes: set[str] = set()
    for i, (kind, text) in enumerate(toks):
        if kind != "id" or text.lower() != "as" or i + 1 >= n or toks[i + 1][1] != "(":
            continue
        j = i - 1
        if j >= 0 and toks[j][1] == ")":
            depth = 0
            while j >= 0:
                if toks[j][1] == ")":
                    depth += 1
                elif toks[j][1] == "(":
                    depth -= 1
                    if depth == 0:
                        break
                j -= 1
            j -= 1
        if j >= 0 and _is_name(toks[j]):
            ctes.add(_ident(toks[j][1]).lower())
    return ctes


def sql_rel_roles(sql: str) -> Roles:
    """Return {(lowercased relation name, 'r' | 'w')} for every grammar relation position.

    CTE names are excluded. A name may carry both roles: the self-terminating INSERT idiom reads
    what it writes, and returning pairs keeps both facts.

    Returns:
        the (name, role) pairs.

    """
    toks = _tokens(sql)
    ctes = _cte_names(toks)
    found = _walk(toks, 0, len(toks), qscope=True)
    return {(name, role) for name, role in found if name not in ctes}


def sql_relnames(sql: str) -> set[str]:
    """Return the lowercased relation names `sql` references (a projection of the roles).

    Returns:
        the names.

    """
    return {name for name, _role in sql_rel_roles(sql)}


def sql_kind(sql: str) -> str:
    """Return the statement's top-level DML/DDL head ('delete', 'insert', 'select', …), or ''.

    ⚑ DEPTH-AWARE, because the first keyword is not the head: `WITH r AS (SELECT …) INSERT INTO …`
    has three heads of which only one is the statement's. Parenthesis depth separates a CTE body
    and a column list from the statement.

    Returns:
        the lowercased head keyword, or the empty string when there is none.

    """
    depth = 0
    for kind, text in _tokens(sql):
        if text == "(":
            depth += 1
        elif text == ")":
            depth -= 1
        elif depth == 0 and kind == "id" and text.lower() in _KIND_HEADS:
            return text.lower()
    return ""


def sql_rw(sql: str) -> tuple[set[str], set[str]]:
    """Return (writes, reads), the relations `sql` writes and the relations it reads.

    ⚑ THE SETS OVERLAP WHEN THE SQL DOES. `writes & reads` is not an error to normalise away: for a
    retire predicate it is precisely the violation, and a union cannot state the property at all.

    Returns:
        the written names and the read names.

    """
    roles = sql_rel_roles(sql)
    return ({n for n, k in roles if k == "w"}, {n for n, k in roles if k == "r"})


def is_sql(text: str) -> bool:
    """Report whether `text` is a SQL statement SQLite's parser accepts.

    ⚑ A HEAD KEYWORD IS NOT A STATEMENT: prose such as `WITH RECURSIVE +` clears a head test, and
    `sqlite3.complete_statement` is a lexer that accepts anything once a `;` is appended. A parser
    is the judge: `EXPLAIN` parses without executing, and `no such table/column` means it PARSED
    (the schema is simply absent). A format placeholder is a value, so it is replaced by `NULL`
    first (`%` is SQLite's modulo and would otherwise kill the house `"… %s" % ph()` idiom).

    Returns:
        whether the text parses as a statement.

    """
    stripped = text.strip().lstrip("(").strip()
    words = stripped.split(None, 1)
    if not words or words[0].lower().strip("(),;") not in _SQL_HEADS:
        return False
    con = sqlite3.connect(":memory:")
    try:
        con.execute("EXPLAIN " + _PLACEHOLDER.sub("NULL", stripped))
    except sqlite3.OperationalError as exc:
        return "no such" in str(exc)
    except sqlite3.Error:
        return False
    finally:
        con.close()
    return True


class RelSite(NamedTuple):
    """One use of a name AS a relation: a SQL literal (`sql`) or an exactly-equal string."""

    path: str
    line: int
    kind: str
    role: str
    context: str
    value: str


def relname_sites(paths: Sequence[str], name: str) -> Found[RelSite]:
    """Return where `name` is used AS A RELATION in `paths`, with the files that were skipped.

    kind `sql`: a SQL literal referencing it in a relation position. kind `name`: a string literal
    EXACTLY equal to it (the `_T("node", …)` shim spelling, roster entries), found beside the SQL
    ones because one question has two spellings. `role` and `context` are the literal's own, from
    `literal_sites`. Prose that merely contains the name is not a hit.

    Returns:
        the sites, with the skipped files.

    """
    low = name.lower()
    out: Found[RelSite] = Found()
    found = literal_sites(paths, "")
    out.skipped.extend(found.skipped)
    for lit in found.rows:
        if lit.value == name:
            out.rows.append(RelSite(lit.path, lit.line, "name", lit.role, lit.context, lit.value))
        if lit.role != "doc" and low in sql_relnames(lit.value) and is_sql(lit.value):
            out.rows.append(RelSite(lit.path, lit.line, "sql", lit.role, lit.context, lit.value))
    out.rows.sort()
    return out
