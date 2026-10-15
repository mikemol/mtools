# W1191: what a published dist's tracked tree and history must not carry (W1144, goal W1143).
#
# Two sets, both data, both judged by the pinned opa:
#   deny      a path or line that must not reach a public index at all (a key, a token, a secret file)
#   withheld  a path or line that a person reads before publishing (a home path, a mail address)
#
# ⚑ A MESSAGE NAMES THE RULE, NEVER THE MATCHED TEXT. The audit's own output is written to logs and
# cards, so echoing a secret would publish it a second time; the scanner reports the rule, the file
# and the line number, and the reader goes to the file.
#
# input: {"path": "<repo-relative path>"} for the path rules, {"line": "<one line of text>"} for
# the content rules. A caller supplies either or both.
package mtools.publish_privacy

import rego.v1

path_deny := {
	"env-file": `(^|/)\.env(\..+)?$`,
	"private-key-file": `(^|/)(id_(rsa|dsa|ecdsa|ed25519)|[^/]+\.(pem|key|p12|pfx|kdbx))$`,
	"credentials-file": `(^|/)(\.netrc|\.pypirc|credentials\.json|\.git-credentials)$`,
}

line_deny := {
	"private-key-block": `-----BEGIN [A-Z ]*PRIVATE KEY-----`,
	"aws-access-key": `\bAKIA[0-9A-Z]{16}\b`,
	"github-token": `\bgh[pousr]_[A-Za-z0-9]{36,}\b`,
	"pypi-token": `\bpypi-AgEI[A-Za-z0-9_-]{20,}`,
	"slack-token": `\bxox[baprs]-[A-Za-z0-9-]{10,}`,
}

line_withheld := {
	"home-path": `/home/[a-z_][a-z0-9_-]*/`,
	# ⚑ NOT PRECEDED BY A BACKSLASH (W1209): source text spells a newline `\n`, so a decorator on the
	# next line read `n@pytest.mark.x` as an address; the local part must start at a line start or
	# after something that is neither a backslash nor part of an address.
	"mail-address": `(^|[^\\A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b`,
}

deny contains sprintf("deny %s", [name]) if {
	some name, pattern in path_deny
	regex.match(pattern, input.path)
}

deny contains sprintf("deny %s", [name]) if {
	some name, pattern in line_deny
	regex.match(pattern, input.line)
}

# EXEMPT (W1148): a match a rule's own exemption recognises is not a finding. ⚑ A mail address at a
# domain reserved for examples and tests (RFC 2606 and 6761) names no one, so a fixture's
# `ada@example.invalid` is not a leak; a real-looking address still is. The exemption is by RULE and
# DATA, never by file, so it cannot hide a real address in a file that also holds placeholders.
#
# A home directory named for nobody (`/home/someone/`, `/home/user/`) is the same case: a placeholder
# a test or a doc uses so as not to name the author. ⚑ THE WHOLE NAME MUST BE ONE OF THEM: the
# pattern is anchored both ends, so `/home/someonelse/` still counts.
exemptions := {
	"mail-address": `@(example\.(com|org|net)|([A-Za-z0-9-]+\.)*invalid|localhost)$`,
	"home-path": `^/home/(someone|user|you|name|me|x|example|username|alice|bob|foo)/$`,
}

exempt(name, found) if regex.match(exemptions[name], found)

hit(name, pattern, line) if {
	some found in regex.find_n(pattern, line, -1)
	not exempt(name, found)
}

withheld contains sprintf("withheld %s", [name]) if {
	some name, pattern in line_withheld
	hit(name, pattern, input.line)
}

# BULK FORM (W1192): input {"files": [{"path": p, "lines": [text, ...]}]}, one evaluation for a
# whole dist. A finding is {kind, rule, path, line}, line 0 for a path rule, and never the text.
# HISTORY FORM (W1193): an entry may also carry "commit", which a finding repeats, so a secret
# that was added and later deleted is still reported with the commit that added it.
tag(file, base) := object.union(base, {"commit": file.commit}) if file.commit

tag(file, base) := base if not file.commit

# ACCEPTED (W1198): a withheld hit a person has read and kept, one entry per file and rule with the
# reason. ⚑ A SUFFIX, so one entry covers the wheel's member and the sdist's (they differ only in the
# prefix). ⚑ NEVER A DENY: only a withheld finding can be accepted, so a secret cannot be waved off
# by adding a line here. A finding that matches carries "accepted": true; the rest do not.
accepted := [
	{
		"path_suffix": "mikemol/hooks/commit_kata.py",
		"rule": "mail-address",
		"reason": "the public no-reply address of the commit trailer",
	},
	{
		"path_suffix": "mikemol/pathsforward/check.py",
		"rule": "home-path",
		"reason": "a placeholder path in a comment",
	},
	{
		"path_suffix": "mikemol/pathsforward/cli.py",
		"rule": "home-path",
		"reason": "a placeholder path in a docstring",
	},
	{
		"path_suffix": "/tests/test_adoption.py",
		"rule": "home-path",
		"reason": "a test of the author's own host layout; it skips when that checkout is absent",
	},
	{
		"path_suffix": "/tests/test_bar_fires.py",
		"rule": "home-path",
		"reason": "comments that describe a path the host once resolved to, as the defect",
	},
	{
		"path_suffix": "/tests/test_no_verify.py",
		"rule": "home-path",
		"reason": "a command line under test that names a host path",
	},
	{
		"path_suffix": "/tests/test_structural_query.py",
		"rule": "home-path",
		"reason": "command lines under test that name a host path",
	},
	{
		"path_suffix": "/tests/test_tick_gate.py",
		"rule": "home-path",
		"reason": "the host's tick prompts, quoted as the input under test",
	},
	{
		"path_suffix": "/policy/standing_test.rego",
		"rule": "home-path",
		"reason": "the standing rules' own tests quote this host's repo layout as the input they judge",
	},
	{
		"path_suffix": "/policy/publish_privacy_test.rego",
		"rule": "home-path",
		"reason": "this policy's tests quote host paths as the input they judge",
	},
	{
		"path_suffix": "/policy/publish_privacy.rego",
		"rule": "home-path",
		"reason": "this policy's comments quote the placeholder path shapes it exempts",
	},
	{
		"path_suffix": "/policy/publish_privacy.rego",
		"rule": "mail-address",
		"reason": "this policy's comments quote the address shapes it matches and exempts",
	},
]

is_accepted(f) if {
	f.kind == "withheld"
	some entry in accepted
	entry.rule == f.rule
	endswith(f.path, entry.path_suffix)
}

mark(f) := object.union(f, {"accepted": true}) if is_accepted(f)

mark(f) := f if not is_accepted(f)

findings contains mark(tag(file, {"kind": "deny", "rule": name, "path": file.path, "line": 0})) if {
	some file in input.files
	some name, pattern in path_deny
	regex.match(pattern, file.path)
}

findings contains mark(tag(file, {"kind": "deny", "rule": name, "path": file.path, "line": n})) if {
	some file in input.files
	some i, text in file.lines
	some name, pattern in line_deny
	regex.match(pattern, text)
	n := i + 1
}

findings contains mark(tag(file, {"kind": "withheld", "rule": name, "path": file.path, "line": n})) if {
	some file in input.files
	some i, text in file.lines
	some name, pattern in line_withheld
	hit(name, pattern, text)
	n := i + 1
}
