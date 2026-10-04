# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
# Hand-written stub: ONLY the pygit2 surface that mikemol.treeio's sources and tests use.
# The bazel mypy runner cannot see runtime dependencies, so without this every pygit2 expression
# is Any under disallow_any_expr. Each signature below was read from pygit2 1.20's own _pygit2.pyi.
# Anything treeio does not call is deliberately absent: a new use is a reviewed change here.

from typing import Literal, overload

from . import enums as enums

class GitError(Exception): ...
class InvalidSpecError(ValueError): ...

class Oid:
    def __eq__(self, other: object) -> bool: ...
    def __hash__(self) -> int: ...

class Signature:
    def __init__(self, name: str, email: str) -> None: ...

class Object:
    name: str | None
    id: Oid
    type_str: Literal["commit", "tree", "tag", "blob"]
    @overload
    def peel(self, target_type: type[Tree], /) -> Tree: ...
    @overload
    def peel(self, target_type: None = None, /) -> Object: ...

class Blob(Object):
    data: bytes

class Tree(Object):
    def __getitem__(self, index: str | int, /) -> Tree | Blob: ...
    def __iter__(self) -> TreeIter: ...

class TreeIter:
    def __iter__(self) -> TreeIter: ...
    def __next__(self) -> Object: ...

class TreeBuilder:
    def insert(self, name: str, oid: Oid, attr: int) -> None: ...
    def write(self) -> Oid: ...

_TreeBuilder = TreeBuilder

class Repository:
    def __init__(self, path: str) -> None: ...
    def revparse_single(self, revision: str, /) -> Object: ...
    def create_blob(self, data: str | bytes) -> Oid: ...
    def TreeBuilder(self) -> _TreeBuilder: ...
    def create_commit(
        self,
        reference_name: str | None,
        author: Signature,
        committer: Signature,
        message: str | bytes,
        tree: Oid,
        parents: list[Oid],
    ) -> Oid: ...

def init_repository(
    path: str, bare: bool = False, *, initial_head: str | None = None
) -> Repository: ...
def hash(data: bytes) -> Oid: ...

__all__ = [
    "Blob",
    "GitError",
    "InvalidSpecError",
    "Object",
    "Oid",
    "Repository",
    "Signature",
    "Tree",
    "TreeBuilder",
    "enums",
    "hash",
    "init_repository",
]
