# W943: `mikemol-new-dist`, so a new distribution is a command and not an afternoon (2026-10-10)

W905 (scaffold htmlstruct) says "with the repo's scaffold tool". There is none: the sibling
`pathwalk` is the smallest library (stdlib only, no scripts) and a new distribution today is a
hand-copy of its files plus three edits to `MODULE.bazel` and one to `INSTALL.md`, each of which the
gate checks and none of which anything generates. The operator's directive is to mechanize the class
of fix rather than hand-fix the instance, and every distribution after this one pays the same cost.

## What a distribution is (measured by listing `git ls-files pathwalk` and `git grep pathwalk`)

Inside `<name>/`: `BUILD.bazel`, `README.md`, `mutants.regex`, `paper.toml`, `pyproject.toml`,
`ratchet-preview.txt` (minted EMPTY: the distribution enters clean), `requirements.txt`,
`requirements-dev.txt`, `rubric.tsv`, `uv.lock`, `warrants.bib`, `src/mikemol/<name>/{__init__.py,
py.typed}`, `tests/`. Outside it, only: `MODULE.bazel` (a `<name>_deps` pip hub beside the library
hubs, a `<name>_dev` uv hub beside the dev hubs, and both names in the `use_repo` list) and
`INSTALL.md` (an alphabetical entry and the count in its first paragraph).

## Design

A pure core and a thin shell, so the tests need no uv, no network and no repository:

- `skeleton(name, description, template)` -> `{relative path: text}`: the template's generic files
  (`BUILD.bazel`, `paper.toml`, `requirements*.txt`, `mutants.regex` emptied, `rubric.tsv` header
  only) with the template's name replaced everywhere (`pathwalk`/`mikemol-pathwalk`); a fresh
  `pyproject.toml` (the template's, cut at `[tool.ruff.lint.per-file-ignores]` and given only
  the smoke test's entry, its description and keywords replaced); a fresh README; the package
  `__init__` and `py.typed`; one smoke test (`tests/test_smoke.py`: the package imports and says its
  name) so the suite is never empty.
- `module_edit(text, name, template)` and `install_edit(text, name, summary)`: pure text transforms.
  The MODULE edit copies the template's `_deps` block, `_dev` block and `use_repo` lines, naming the
  new distribution; the INSTALL edit inserts the entry in alphabetical order and bumps "There are N".
- The shell writes the files, applies the two edits, runs `uv lock` in the new directory (the
  lock embeds the project's name, so it cannot be copied) and prints the remaining steps by name:
  `bazel build //<name>:.venv`, the uv venv, `mikemol-gen-warrants` for the smoke test, then the
  commit. It refuses an existing directory, a name that is not `[a-z][a-z0-9]*`, and a template that
  is missing.

## Slices

| card | what |
| --- | --- |
| W944 | the pure core: `skeleton`, `module_edit`, `install_edit`, with tests over text fixtures. |
| W945 | the shell and the console script `mikemol-new-dist`, run against a throwaway copy of the repository's real files (not the live tree). |
| W905 | use it for `htmlstruct`, the first real consumer (one new dist at a time: memory untracked-dist-breaks-gate). |
