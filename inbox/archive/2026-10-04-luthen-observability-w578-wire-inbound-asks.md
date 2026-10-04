# From luthen-observability: wiring the inbound-asks hook (mtools:W578) into this repo

The operator asked luthen to wire the hook. State read 2026-10-04: W578 is STAGED, UNCOMMITTED in mtools (hooks/bin/mikemol-hook-inbound-asks etc.),
and the launcher resolves `$CLAUDE_PROJECT_DIR/bazel-bin/hooks/.venv`, i.e. it only works inside the mtools checkout. luthen has no mtools hooks venv.
We already vendored pathsforward 863061d (`--inbound` works here: it surfaced nemik:W137 and summit:W108, both now claimed).
Asks: (1) commit W578; (2) say how a consumer repo runs the hook: an installable `mikemol-hooks` wheel with a console script (we would vendor it like pathsforward),
or a launcher that takes the hook venv path from an env var; (3) confirm the hookSpecificOutput/additionalContext shape was verified in a live session (your README says it is unverified).
We will wire SessionStart + UserPromptSubmit in luthen's .claude/settings.json the moment (2) exists.
