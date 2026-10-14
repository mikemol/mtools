# Each rule: a witness that must fire, and a near-miss control that must not.
# ⚑ THE SECRET-SHAPED WITNESSES ARE BUILT BY concat, so this file does not itself match the rules
# it tests (the audit scans this tree).
package mtools.publish_privacy_test

import rego.v1

import data.mtools.publish_privacy

path_denies(path, name) if {
	sprintf("deny %s", [name]) in publish_privacy.deny with input as {"path": path}
}

line_denies(line, name) if {
	sprintf("deny %s", [name]) in publish_privacy.deny with input as {"line": line}
}

line_withholds(line, name) if {
	sprintf("withheld %s", [name]) in publish_privacy.withheld with input as {"line": line}
}

test_env_file_witness if path_denies("pkg/.env", "env-file")

test_env_file_variant_witness if path_denies(".env.production", "env-file")

test_env_file_control if not path_denies("docs/environment.md", "env-file")

test_env_example_control if not path_denies("pkg/.environment", "env-file")

test_private_key_file_witness if path_denies("deploy/id_ed25519", "private-key-file")

test_pem_witness if path_denies("certs/server.pem", "private-key-file")

test_private_key_file_control if not path_denies("src/keyboard.py", "private-key-file")

test_credentials_file_witness if path_denies("home/.pypirc", "credentials-file")

test_credentials_file_control if not path_denies("docs/pypirc-howto.md", "credentials-file")

test_private_key_block_witness if line_denies(concat("", ["-----BEGIN RSA ", "PRIVATE KEY-----"]), "private-key-block")

test_private_key_block_control if not line_denies("-----BEGIN CERTIFICATE-----", "private-key-block")

test_aws_key_witness if line_denies(concat("", ["id = AKIA", "ABCDEFGHIJKLMNOP"]), "aws-access-key")

test_aws_key_control if not line_denies("AKIAshort", "aws-access-key")

test_github_token_witness if line_denies(concat("", ["token ghp_", "0123456789abcdefghijklmnopqrstuvwxyzAB"]), "github-token")

test_github_token_control if not line_denies("ghp_tooshort", "github-token")

test_pypi_token_witness if line_denies(concat("", ["password = pypi-", "AgEIcHlwaS5vcmcAAAAAAAAAAAAAAAAAAA"]), "pypi-token")

test_pypi_token_control if not line_denies("uploads to pypi-org mirrors", "pypi-token")

test_slack_token_witness if line_denies(concat("", ["xo", "xb-1234567890-abcdef"]), "slack-token")

test_slack_token_control if not line_denies("xoxo friends", "slack-token")

test_home_path_witness if line_withholds(concat("", ["/ho", "me/someone/project"]), "home-path")

test_home_path_control if not line_withholds("/usr/home-like/x and ~/project", "home-path")

test_mail_address_witness if line_withholds(concat("", ["write to a", "@example.org"]), "mail-address")

test_mail_address_control if not line_withholds("decorator @property and a@b", "mail-address")

# a withheld line is not a deny, and a deny line is not withheld by the deny rules
test_withheld_is_not_deny if not line_denies(concat("", ["/ho", "me/someone/x"]), "home-path")

test_clean_line_fires_nothing if {
	count(publish_privacy.deny) == 0 with input as {"path": "src/mod.py", "line": "x = 1"}
	count(publish_privacy.withheld) == 0 with input as {"path": "src/mod.py", "line": "x = 1"}
}

bulk := {"files": [
	{"path": "a/.env", "lines": ["x = 1"]},
	{"path": "a/mod.py", "lines": ["ok", concat("", ["/ho", "me/someone/x"]), concat("", ["id AKIA", "ABCDEFGHIJKLMNOP"])]},
]}

test_bulk_findings_carry_rule_path_and_line if {
	publish_privacy.findings == {
		{"kind": "deny", "rule": "env-file", "path": "a/.env", "line": 0},
		{"kind": "withheld", "rule": "home-path", "path": "a/mod.py", "line": 2},
		{"kind": "deny", "rule": "aws-access-key", "path": "a/mod.py", "line": 3},
	} with input as bulk
}

test_history_entries_repeat_their_commit_in_each_finding if {
	publish_privacy.findings == {{"kind": "deny", "rule": "env-file", "path": "a/.env", "line": 0, "commit": "abc"}} with input as {"files": [{"commit": "abc", "path": "a/.env", "lines": []}]}
}

test_bulk_clean_input_has_no_findings if {
	count(publish_privacy.findings) == 0 with input as {"files": [{"path": "a/mod.py", "lines": ["x"]}]}
}

# the message carries the rule name and never the text that matched
test_message_does_not_echo_the_match if {
	msgs := publish_privacy.withheld with input as {"line": concat("", ["/ho", "me/someone/x"])}
	every msg in msgs {
		not contains(msg, "someone")
	}
}
