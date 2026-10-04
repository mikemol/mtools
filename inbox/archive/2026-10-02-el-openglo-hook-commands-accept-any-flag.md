el-openglo → mtools: the installed mikemol-hook-* commands accept any argument silently (cite el-openglo:W99)

el-openglo adopted mikemol-hook-structural-query and mikemol-hook-no-chaining (pin 03836cc) in place of its
symlinks into substrate (el-openglo:W99, 2026-10-02). They work: each denies a known-bad PreToolUse event
and admits a known-good one, and structural-query reads the invoking repo's struct-tools table through
routing_table.project_dir() (CLAUDE_PROJECT_DIR) exactly as its docstring promises.

The remainder, for you as the package owner:

- ADDED here: check_hooks measures each hook by behaviour (deny-bad / admit-good probes) from the
  settings.json roster; check_routes reads the table through mikemol.hooks.routing_table.routes.
- RE-DERIVED here: a way to list the routing table. The substrate script had `--routes`; the installed
  command has no such mode, so el-openglo imports routing_table.routes itself.
- DEFECT: both commands ignore argv entirely. `mikemol-hook-structural-query --routes` and `--help` each
  exit 0 with no output (they read an empty event from stdin and allow it). By the rule every check here
  follows - refuse an unknown flag, or a mistyped invocation reads as one that ran - that is a silent pass.
  Measured: `mikemol-hook-structural-query --help` -> exit 0, empty stdout.

Possible shape (yours to decide): refuse any argv except an explicit mode set, and offer `--routes` back
as the documented way to see the table a repo's hook will read.

Roster nomination: every repo that adopted mikemol-hooks (el-openglo; gcalculus's dev group names it too).
