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
	"mail-address": `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b`,
}

deny contains sprintf("deny %s", [name]) if {
	some name, pattern in path_deny
	regex.match(pattern, input.path)
}

deny contains sprintf("deny %s", [name]) if {
	some name, pattern in line_deny
	regex.match(pattern, input.line)
}

withheld contains sprintf("withheld %s", [name]) if {
	some name, pattern in line_withheld
	regex.match(pattern, input.line)
}

# BULK FORM (W1192): input {"files": [{"path": p, "lines": [text, ...]}]}, one evaluation for a
# whole dist. A finding is {kind, rule, path, line}, line 0 for a path rule, and never the text.
findings contains {"kind": "deny", "rule": name, "path": file.path, "line": 0} if {
	some file in input.files
	some name, pattern in path_deny
	regex.match(pattern, file.path)
}

findings contains {"kind": "deny", "rule": name, "path": file.path, "line": n} if {
	some file in input.files
	some i, text in file.lines
	some name, pattern in line_deny
	regex.match(pattern, text)
	n := i + 1
}

findings contains {"kind": "withheld", "rule": name, "path": file.path, "line": n} if {
	some file in input.files
	some i, text in file.lines
	some name, pattern in line_withheld
	regex.match(pattern, text)
	n := i + 1
}
