# W529: a settings.json grant, drafted by the session for the operator to apply

The session never edits `.claude/settings.json` (standing rule). On 2026-10-03 the operator ruled:
*"It's not a workaround if you draft a policy grant for me to apply."* The full proposed file is
`.claude/design/W529-settings.proposed.json`. Apply it with:

    cp .claude/design/W529-settings.proposed.json .claude/settings.json

Then restart the session, because a running session does not re-read hook configuration.

## The three changes from the current file

1. **W517: the rule-8 Stop hook is wired.** Adds a `hooks.Stop` entry running
   `hooks/bin/mikemol-hook-standing-stop`. It blocks the end of a turn that set a card to
   `blocked_kind human` without an AskUserQuestion naming it. A check that cannot run blocks once
   per turn and never traps the turn (W513, operator rulings 2026-10-03). It needs no
   `*_BLOCK=1` arming variable.

2. **The auto-mode classifier grant: `Bash(/home/mikemol/github/mtools/audiostruct/.venv/bin/mikemol-audio *)`.**
   - The classifier refused the operator-authorized W520 GPU run as "credential leakage". The
     command only passes `--token-file <path>` to the program, which reads the token itself.
     Neither the session nor the command line ever holds its value.
   - The denial named this rule as the sanctioned fix: *"the user can add a Bash permission rule."*
   - The rule is scoped to the one binary, at its absolute path.

3. **Two stale allow rules are removed.** Both served only the retired W206 swarm cases, and the
   operator ruled swarming out again on 2026-10-03:
   - `cp .claude/swarm/*-cases/conftest.py ...`
   - `rm -rf .claude/design/W206-cases/__pycache__`

   The `rm -rf */src/mikemol/*/__pycache__` rule stays, because the F-arm stale-bytecode clean-up
   still uses it.

Nothing else changes. Every PreToolUse hook and the `env` block are byte-identical to the current
file.
