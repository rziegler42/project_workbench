"""The code checks for `commit` (`docs/specs/action-review.md`, "The checks"; the counterparts are those of
`docs/specs/safe-git.md`, "Each check of the approver, and where it goes").

Plan `2026-10-26-action-review-engine`, increment F. A check is a pure function of the `describe` object, so the
checks are tested on objects built by hand and on the objects the real `safe-git describe commit` prints for a scratch
repository. The secret scan is tested on text built at run time from pieces, so that no secret-looking line is in this
file, and a test never asserts on, or prints, the text a pattern matched."""

import copy
import io
import json
import os
import subprocess
import tempfile
import time
import unittest
import unittest.mock

from tests import support_helpers, support_install

HEAD = "a" * 40
DIFF = "--- HEAD/a.txt\n+++ work/a.txt\n@@ -1 +1 @@\n-one\n+two\n"
FACTS = {
    "head": HEAD, "expected_head": HEAD, "leave_other_staged": False, "path_count": 1, "subject": "Change a",
    "trailers": [], "body": None, "attribution_allowed": False, "program_findings": [], "staged_paths": [],
    "requested_paths": ["a.txt"], "paths": ["a.txt"], "new_paths": [], "modified_paths": ["a.txt"],
    "deleted_paths": [], "unchanged_paths": [], "binary_paths": [], "not_regular_paths": [], "diff": DIFF,
    "omitted": [],
}
ALL = ("head_matches", "repo_config_safe", "staging_state_ok", "paths_valid", "message_valid",
       "paths_not_credentials", "paths_regular", "facts_complete", "no_secret_lines")
NAMES = (".env", "id_rsa*", "*.pem", ".pem", "credentials", ".ssh/")

# The error codes of `describe commit` and the check each one fails (spec, "The checks").
CODES = {
    "head_matches": ("expected_head_invalid", "head_mismatch", "head_unreadable"),
    "repo_config_safe": ("repo_selects_program", "operation_in_progress"),
    "staging_state_ok": ("index_has_staged_changes", "path_already_staged"),
    "paths_valid": ("usage", "path_refused", "path_duplicate", "path_unmerged", "path_in_nested_repository",
                    "path_not_a_file", "path_unknown", "path_converts_on_add", "whitespace_errors"),
    "message_valid": ("subject_invalid", "body_invalid", "trailer_invalid", "message_character_refused",
                      "attribution_refused", "setting_invalid"),
    "facts_complete": ("repository_unreadable", "index_unreadable"),
}


def doc(ok=True, truncated=False, errors=(), **facts):
    return {"contract": 1, "action": "commit", "ok": ok, "truncated": truncated,
            "errors": [{"code": code, "message": "m"} for code in errors], "facts": dict(FACTS, **facts)}


def refused(*codes):
    """What a refusal looks like: no fact the refusal prevented, the others as given."""
    facts = {name: ([] if isinstance(value, list) else None if isinstance(value, (str, type(None))) else value)
             for name, value in FACTS.items()}
    return {"contract": 1, "action": "commit", "ok": False, "truncated": False,
            "errors": [{"code": code, "message": "m"} for code in codes], "facts": facts}


def without_fact(document, name):
    result = copy.deepcopy(document)
    del result["facts"][name]
    return result


def piece(*parts):
    return "".join(parts)


def section(path, *added):
    count = len(added)
    return "--- HEAD/%s\n+++ work/%s\n@@ -0,0 +1%s @@\n%s" % (
        path, path, ",%d" % count if count != 1 else "", "".join("+%s\n" % line for line in added))


KEY = piece("-----BEGIN ", "RSA PRIVATE", " KEY-----")
AWS = piece("AK", "IA", "ABCDEFGHIJKLMNOP")
GITHUB = piece("gh", "p_", "a" * 36)
LOGIN = piece("pass", "word", ' = "', "x" * 12, '"')
URL = piece("https", "://", "u", ":", "p", "@", "host.invalid/")
RANDOM = piece("aB3dE5gH7jK9mN2", "pQ4sT6vW8yZ1xC0")
HEX64 = "0123456789abcdef" * 4


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper = support_helpers.load("action-review")

    def rule(self, checks=ALL, lists=None, action="commit"):
        lists = {"credential_names": NAMES} if lists is None else lists
        return self.helper.Rule("safe-git-%s.json" % action, ("wb", "run", "safe-git"), action, "safe-git", action,
                                {}, None, tuple(checks), action, (), lists)

    def run_checks(self, document, **options):
        return self.helper.run_checks(self.rule(**options), document)


class SecretScan(Base):
    def kind(self, text, **options):
        return self.helper.secret_kind(text, **options)

    def test_each_kind_of_secret_shape_is_named_by_its_kind_and_not_by_its_text(self):
        for text in (KEY, AWS, GITHUB, LOGIN, URL, "Bearer " + "a" * 20, "token: " + "q" * 14):
            self.assertEqual("pattern", self.kind(text))
        self.assertEqual("long_hex", self.kind(HEX64))
        self.assertEqual("high_entropy", self.kind(RANDOM))

    def test_ordinary_text_is_not_a_secret(self):
        for text in ("", "Change a", "the quick brown fox", "a" * 40, "0123456789abcdef0123456789abcdef01234567",
                     "see docs/specs/action-review.md for the details", "test_observation_includes_public_history"):
            self.assertIsNone(self.kind(text))

    def test_a_long_line_of_a_scheme_like_run_is_scanned_in_linear_time(self):
        # Security pass, finding 4: the scheme part of the URL pattern was unanchored, so a 98,000 character lowercase
        # line took about 30 seconds, past the hook's limit.
        for unit in ("z", "q1", "q.", "q-", "q+"):
            diff = section("a.txt", (unit * 98000)[:98000])
            started = time.monotonic()
            self.assertIsNone(self.helper.diff_secret_kind(diff), unit)
            self.assertLess(time.monotonic() - started, 5, unit)

    def test_a_credential_in_a_url_is_seen_after_a_long_run_and_after_a_digit(self):
        for text in ("z" * 40 + "://u:p@host.invalid/", "1https://u:p@host.invalid/"):
            self.assertEqual("pattern", self.kind(text), text)

    def test_a_marker_of_a_diff_line_does_not_hide_a_secret(self):
        self.assertEqual("pattern", self.kind("+" + AWS + "\n"))

    def test_a_secret_written_with_escapes_is_seen(self):
        self.assertEqual("pattern", self.kind("".join("%%%02X" % ord(c) for c in AWS)))
        self.assertEqual("pattern", self.kind("".join("\\u%04x" % ord(c) for c in AWS)))

    def test_the_entropy_check_can_be_skipped_and_the_generic_patterns_relaxed(self):
        self.assertIsNone(self.kind(RANDOM, entropy=False))
        self.assertEqual("pattern", self.kind(AWS, entropy=False))
        self.assertIsNone(self.kind(LOGIN, relaxed=True))
        self.assertEqual("pattern", self.kind(AWS, relaxed=True))

    def test_a_digest_on_a_line_that_says_so_is_not_a_secret_and_a_bare_one_is(self):
        self.assertIsNone(self.kind("checksum: " + HEX64))
        self.assertEqual("long_hex", self.kind("value " + HEX64))

    def test_a_lock_file_skips_only_the_entropy_check(self):
        self.assertIsNone(self.helper.diff_secret_kind(section("package-lock.json", RANDOM)))
        self.assertEqual("pattern", self.helper.diff_secret_kind(section("package-lock.json", AWS)))
        self.assertEqual("high_entropy", self.helper.diff_secret_kind(section("src/lock.json", RANDOM)))

    def test_a_test_directory_relaxes_only_the_generic_assignment_patterns(self):
        self.assertIsNone(self.helper.diff_secret_kind(section("tests/fixture.py", LOGIN)))
        self.assertEqual("pattern", self.helper.diff_secret_kind(section("tests/fixture.py", AWS)))
        self.assertEqual("pattern", self.helper.diff_secret_kind(section("src/fixture.py", LOGIN)))
        self.assertEqual("pattern", self.helper.diff_secret_kind(section("tests", LOGIN)))

    def test_each_file_of_a_diff_is_scanned_under_its_own_options(self):
        diff = section("package-lock.json", RANDOM) + section("src/a.py", RANDOM)
        self.assertEqual("high_entropy", self.helper.diff_secret_kind(diff))
        self.assertIsNone(self.helper.diff_secret_kind(section("package-lock.json", RANDOM)
                                                       + section("tests/a.py", LOGIN)))

    def test_a_line_that_looks_like_a_file_header_inside_a_hunk_changes_no_option(self):
        spoof = ("--- HEAD/src/a.py\n+++ work/src/a.py\n@@ -1 +1,2 @@\n--- HEAD/package-lock.json\n"
                 "+++ work/package-lock.json\n+" + RANDOM + "\n")
        self.assertEqual("high_entropy", self.helper.diff_secret_kind(spoof))

    def test_a_diff_whose_shape_is_not_understood_is_scanned_as_a_whole(self):
        for diff in (RANDOM, "garbage\n" + RANDOM + "\n", "--- HEAD/package-lock.json\n+++ work/other\n+" + RANDOM + "\n",
                     "--- HEAD/package-lock.json\n+++ work/package-lock.json\n@@ -0,0 +1 @@\n+a\n+" + RANDOM + "\n",
                     "--- HEAD/package-lock.json\n+++ work/package-lock.json\n@@ -0,0 +1,9 @@\n+" + RANDOM + "\n",
                     "--- HEAD/package-lock.json\n+++ work/package-lock.json\n@@ nonsense @@\n+" + RANDOM + "\n"):
            self.assertEqual("high_entropy", self.helper.diff_secret_kind(diff))

    def test_a_mode_line_and_a_missing_final_newline_are_part_of_a_diff_that_is_understood(self):
        diff = ("mode HEAD/run.sh 100644 -> work/run.sh 100755\n"
                "--- HEAD/package-lock.json\n+++ work/package-lock.json\n@@ -1 +1 @@\n-a\n+" + RANDOM
                + "\n\\ No newline at end of file\n")
        self.assertIsNone(self.helper.diff_secret_kind(diff))
        self.assertEqual("pattern", self.helper.diff_secret_kind("mode HEAD/" + AWS + " 100644 -> work/x 100755\n"))

    def test_a_hunk_header_with_an_absurd_count_is_a_shape_not_understood_and_not_an_error(self):
        diff = "--- HEAD/package-lock.json\n+++ work/package-lock.json\n@@ -0,0 +1,%s @@\n+%s\n" % ("9" * 5000, RANDOM)
        self.assertIsNotNone(self.helper.diff_secret_kind(diff))

    def test_an_empty_diff_has_no_secret(self):
        self.assertIsNone(self.helper.diff_secret_kind(""))


class CredentialNames(Base):
    def hit(self, path, names=NAMES):
        return self.helper.credential_path(path, names)

    def test_a_listed_name_matches_the_final_segment_in_any_case(self):
        for path in (".env", "a/.env", "a/b/.ENV", "A/Credentials", "x/id_rsa", "x/ID_RSA.pub", "dir/id_rsa_backup"):
            self.assertTrue(self.hit(path), path)

    def test_an_extension_that_begins_with_a_dot_ends_the_name(self):
        self.assertTrue(self.hit("a/server.pem"))
        self.assertTrue(self.hit("a/SERVER.PEM"))
        self.assertTrue(self.hit("a/x.env"))
        self.assertFalse(self.hit("a/pem"))

    def test_a_name_that_does_not_begin_with_a_dot_is_not_a_suffix(self):
        self.assertFalse(self.hit("a/mycredentials"))
        self.assertTrue(self.hit("a/credentials"))
        self.assertFalse(self.hit("credentials/readme.md"))

    def test_only_the_final_segment_is_matched_against_a_name(self):
        self.assertFalse(self.hit(".env/readme.md"))
        self.assertFalse(self.hit("id_rsa/readme.md"))

    def test_a_star_stands_for_any_run_of_characters_within_the_final_segment(self):
        self.assertTrue(self.hit("a/id_rsa"))
        self.assertTrue(self.hit("a/id_rsa.old"))
        self.assertFalse(self.hit("a/id_dsa"))
        self.assertTrue(self.hit("a/x.pem", ("*.pem",)))
        self.assertFalse(self.hit("a/x.pem.txt", ("*.pem",)))

    def test_an_entry_with_a_final_slash_names_a_directory_anywhere_above_the_file(self):
        self.assertTrue(self.hit(".ssh/config"))
        self.assertTrue(self.hit("home/.ssh/known_hosts"))
        self.assertTrue(self.hit("home/.SSH/a/b/c"))
        self.assertFalse(self.hit("home/ssh/config"))
        self.assertFalse(self.hit("a/.ssh"))
        self.assertTrue(self.hit(".config/gh/hosts.yml", (".config/gh/",)))
        self.assertTrue(self.hit("home/.config/gh/hosts.yml", (".config/gh/",)))
        self.assertFalse(self.hit("home/x.config/gh/hosts.yml", (".config/gh/",)))
        self.assertFalse(self.hit("home/.config/ghost/hosts.yml", (".config/gh/",)))

    def test_no_list_matches_nothing(self):
        self.assertFalse(self.hit(".env", ()))

    def test_the_shipped_list_also_covers_the_names_the_security_pass_found_missing(self):
        path = os.path.join(support_install.ROOT, "packages", "workbench", "action-review", "rules",
                            "safe-git-commit.json")
        with open(path, encoding="utf-8") as handle:
            names = json.load(handle)["lists"]["credential_names"]
        for credential in ("prod.tfvars", "infra/terraform.tfvars", "AuthKey.p8", ".dockercfg",
                           "application_default_credentials.json", ".vault-pass", ".vault_pass", "htpasswd",
                           "secrets/db.yaml", "deploy/secrets/prod.env.txt"):
            self.assertTrue(self.hit(credential, names), credential)
        for ordinary in ("a.tfvars.md", "docs/p8.md", "secretsanta/a.txt", "htpasswd.md"):
            self.assertFalse(self.hit(ordinary, names), ordinary)

    def test_the_shipped_list_covers_what_the_approver_covered(self):
        path = os.path.join(support_install.ROOT, "packages", "workbench", "action-review", "rules",
                            "safe-git-commit.json")
        with open(path, encoding="utf-8") as handle:
            names = json.load(handle)["lists"]["credential_names"]
        self.assertLessEqual(len(names), 256)
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual([name.lower() for name in names], names)
        for credential in (".env", "app/.env", ".env.local", "id_rsa", "id_rsa.pub", "id_dsa", "id_ecdsa", "id_ed25519",
                           "a/b/server.pem", "a.key", "a.p12", "a.pfx", "a.keystore", "a.jks", ".netrc", "_netrc",
                           ".npmrc", ".pypirc", ".git-credentials", "credentials", "credentials.json", "secrets.yml",
                           "secret.txt", "a.kdbx", "a.ovpn", ".pgpass", ".htpasswd", ".boto", "kubeconfig",
                           "a.tfstate", "a.tfstate.backup", "service-account-prod.json", "my_id_rsa_old",
                           "token", "token.txt", "a.token", ".ssh/config", ".aws/config", ".gnupg/pubring.kbx",
                           ".kube/config", ".docker/config.json", ".config/gh/hosts.yml", ".git/config",
                           "x/.git/hooks/pre-commit", "A/.ENV", "x/ID_RSA"):
            self.assertTrue(self.hit(credential, names), credential)
        for ordinary in ("README.md", "src/main.py", "docs/specs/action-review.md", "src/environment.py", ".envrc",
                         "keyboard.txt", "a/ssh/config", "src/credential.py", "id.txt", "a.txt"):
            self.assertFalse(self.hit(ordinary, names), ordinary)


class Checking(Base):
    def test_a_good_commit_object_fails_no_check(self):
        self.assertEqual((), self.run_checks(doc()))

    def test_the_result_is_a_tuple_of_check_names_in_the_order_of_the_engines_list_not_the_rule(self):
        bad = doc(head="b" * 40, staged_paths=["z"], not_regular_paths=["a.txt"], subject=AWS)
        failed = self.run_checks(bad, checks=tuple(reversed(ALL)))
        self.assertEqual(("head_matches", "staging_state_ok", "paths_regular", "no_secret_lines"), failed)
        self.assertIsInstance(failed, tuple)

    def test_a_check_the_rule_does_not_name_is_not_run(self):
        bad = doc(head="b" * 40, staged_paths=["z"])
        self.assertEqual(("head_matches",), self.run_checks(bad, checks=("head_matches", "paths_regular")))
        self.assertEqual((), self.run_checks(bad, checks=("paths_regular",)))

    def test_a_check_with_no_function_fails_and_names_itself(self):
        functions = {name: f for name, f in self.helper.CHECK_FUNCTIONS.items() if name != "paths_regular"}
        with unittest.mock.patch.dict(self.helper.CHECK_FUNCTIONS, functions, clear=True):
            self.assertEqual(("paths_regular",), self.run_checks(doc()))

    def test_head_matches(self):
        for facts in ({"head": "b" * 40}, {"expected_head": "b" * 40}, {"head": None},
                      {"head": None, "expected_head": None}, {"head": HEAD, "expected_head": None},
                      {"head": HEAD, "expected_head": "none"}):
            self.assertEqual(("head_matches",), self.run_checks(doc(**facts)), facts)
        self.assertEqual((), self.run_checks(doc(head=None, expected_head="none")))

    def test_repo_config_safe(self):
        self.assertEqual(("repo_config_safe",), self.run_checks(doc(program_findings=["core.fsmonitor"])))

    def test_staging_state_ok(self):
        self.assertEqual(("staging_state_ok",), self.run_checks(doc(staged_paths=["b.txt"])))
        self.assertEqual((), self.run_checks(doc(staged_paths=["b.txt"], leave_other_staged=True)))
        self.assertEqual((), self.run_checks(doc(staged_paths=[], leave_other_staged=True)))

    def test_paths_not_credentials_reads_the_requested_paths_and_the_validated_ones(self):
        self.assertEqual(("paths_not_credentials",), self.run_checks(doc(requested_paths=["x/.env"])))
        self.assertEqual(("paths_not_credentials",), self.run_checks(doc(paths=["id_rsa"])))
        self.assertEqual((), self.run_checks(doc(requested_paths=["x/a.txt"], paths=["x/a.txt"])))

    def test_paths_not_credentials_fails_without_the_list_it_reads(self):
        for lists in (None, {}, {"reviewer_facing_paths": ("AGENTS.md",)}):
            rule = self.helper.Rule("safe-git-commit.json", ("wb", "run", "safe-git"), "commit", "safe-git", "commit",
                                    {}, None, ALL, "commit", (), lists)
            self.assertEqual(("paths_not_credentials",), self.helper.run_checks(rule, doc()))
        rule = self.helper.Rule("safe-git-commit.json", ("wb", "run", "safe-git"), "commit", "safe-git", "commit",
                                {}, None, ALL, "commit", (), {"credential_names": ()})
        self.assertEqual((), self.helper.run_checks(rule, doc()))

    def test_paths_regular(self):
        self.assertEqual(("paths_regular",), self.run_checks(doc(not_regular_paths=["a.txt"])))

    def test_facts_complete(self):
        self.assertEqual(("facts_complete",), self.run_checks(doc(truncated=True)))
        self.assertEqual(("facts_complete",), self.run_checks(doc(binary_paths=["a.bin"])))

    def test_no_secret_lines_reads_the_diff_the_subject_the_body_and_each_trailer(self):
        for facts in ({"diff": section("a.txt", AWS)}, {"subject": GITHUB}, {"body": KEY},
                      {"trailers": ["Plan: x", "Key: " + URL]}, {"diff": section("src/a.py", RANDOM)}):
            self.assertEqual(("no_secret_lines",), self.run_checks(doc(**facts)), list(facts))
        self.assertEqual((), self.run_checks(doc(diff=section("package-lock.json", RANDOM))))
        self.assertEqual((), self.run_checks(doc(body="a body", trailers=["Plan: a#B"])))

    def test_an_object_that_is_not_ok_fails_the_check_that_each_error_code_names(self):
        for name, codes in CODES.items():
            for code in codes:
                failed = self.run_checks(refused(code))
                self.assertIn(name, failed, code)
                self.assertTrue(failed, code)

    def test_an_error_code_that_only_the_named_check_reads_fails_that_check_alone_on_a_complete_object(self):
        for name, codes in CODES.items():
            for code in codes:
                self.assertEqual((name,), self.run_checks(doc(ok=False, errors=(code,))), code)

    def test_an_error_code_with_no_mapping_fails_facts_complete(self):
        for code in ("unheard_of", "target_missing", "git_metadata_refused"):
            self.assertEqual(("facts_complete",), self.run_checks(doc(ok=False, errors=(code,))), code)

    def test_ok_false_with_no_error_fails_facts_complete(self):
        self.assertEqual(("facts_complete",), self.run_checks(doc(ok=False)))

    def test_a_failure_that_the_rule_does_not_name_is_reported_as_facts_complete(self):
        bad = doc(ok=False, errors=("head_mismatch", "subject_invalid"))
        self.assertEqual(("head_matches", "message_valid"), self.run_checks(bad))
        self.assertEqual(("head_matches", "facts_complete"), self.run_checks(bad, checks=("head_matches",)))
        self.assertEqual(("facts_complete",), self.run_checks(bad, checks=("paths_regular",)))

    def test_two_codes_for_one_check_name_it_once(self):
        self.assertEqual(("paths_valid",), self.run_checks(doc(ok=False, errors=("usage", "path_refused"))))

    NEEDS = {
        "head_matches": ("head", "expected_head"), "repo_config_safe": ("program_findings",),
        "staging_state_ok": ("staged_paths", "leave_other_staged"), "paths_not_credentials": ("requested_paths", "paths"),
        "paths_regular": ("not_regular_paths",), "facts_complete": ("binary_paths",),
        "no_secret_lines": ("diff", "subject", "body", "trailers"),
    }

    def test_a_fact_that_a_check_reads_and_that_is_absent_fails_that_check_and_facts_complete(self):
        for check, names in self.NEEDS.items():
            for name in names:
                failed = self.run_checks(without_fact(doc(), name))
                self.assertIn(check, failed, name)
                self.assertIn("facts_complete", failed, name)

    def test_a_fact_of_the_wrong_type_fails_that_check_and_facts_complete(self):
        wrong = {"head": 5, "expected_head": ["x"], "program_findings": "none", "staged_paths": None,
                 "leave_other_staged": "no", "requested_paths": "a.txt", "paths": 3, "not_regular_paths": None,
                 "binary_paths": "no", "diff": [], "subject": 5, "body": ["b"], "trailers": "Plan: x"}
        owner = {name: check for check, names in self.NEEDS.items() for name in names}
        for name, value in wrong.items():
            failed = self.run_checks(doc(**{name: value}))
            self.assertIn(owner[name], failed, name)
            self.assertIn("facts_complete", failed, name)

    def test_a_list_of_something_other_than_text_is_the_wrong_type(self):
        for name in ("program_findings", "staged_paths", "requested_paths", "paths", "not_regular_paths",
                     "binary_paths", "trailers"):
            self.assertIn("facts_complete", self.run_checks(doc(**{name: [1]})), name)

    def test_a_fact_that_no_check_reads_does_not_matter(self):
        document = doc()
        del document["facts"]["unchanged_paths"]
        document["facts"]["something_new"] = "x"
        self.assertEqual((), self.run_checks(document))

    def test_a_null_text_fact_of_an_object_that_is_not_ok_is_nothing_to_scan(self):
        failed = self.run_checks(refused("subject_invalid"))
        self.assertIn("message_valid", failed)
        self.assertNotIn("no_secret_lines", failed)

    def test_a_null_text_fact_of_an_ok_object_is_a_missing_fact(self):
        for name in ("subject", "diff"):
            failed = self.run_checks(doc(**{name: None}))
            self.assertIn("no_secret_lines", failed, name)
            self.assertIn("facts_complete", failed, name)

    def test_the_failed_checks_hold_only_names_of_the_fixed_list(self):
        bad = doc(head="b" * 40, subject=AWS, diff=section("a.txt", GITHUB), body=KEY, requested_paths=[".env"])
        for name in self.run_checks(bad):
            self.assertIn(name, self.helper.CHECKS)
            self.assertNotIn(AWS, name)


class RealCommit(Base):
    """The objects the real `safe-git describe commit` prints for a scratch repository."""

    def setUp(self):
        self.safe_git = support_helpers.load("safe-git")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = os.path.realpath(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        self.write("a.txt", "one\n")
        self.git("add", "a.txt")
        self.git("commit", "-q", "-m", "first")
        self.head = self.git("rev-parse", "HEAD").strip()
        self.write("a.txt", "two\n")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.dir, check=True, capture_output=True, text=True).stdout

    def write(self, name, text):
        mode = "wb" if isinstance(text, bytes) else "w"
        with open(os.path.join(self.dir, name), mode) as handle:
            handle.write(text)

    def checked(self, *paths, head=None, subject="Change a", extra=(), **options):
        args = ["describe", "commit", "--expected-head", head or self.head, "--subject", subject, *extra, "--",
                *(paths or ("a.txt",))]
        out, err = io.StringIO(), io.StringIO()
        code = self.safe_git.main(args, out, err, self.dir)
        self.assertEqual(0, code, err.getvalue()[:200])
        document = self.helper.read_description(out.getvalue().encode("utf-8"), "commit")
        return self.run_checks(document, **options)

    def test_a_plain_change_fails_no_check(self):
        self.assertEqual((), self.checked())

    def test_a_head_that_does_not_match(self):
        self.assertIn("head_matches", self.checked(head="0" * 40))

    def test_a_staged_path_without_leave_other_staged(self):
        self.write("b.txt", "b\n")
        self.git("add", "b.txt")
        self.assertIn("staging_state_ok", self.checked())
        self.assertEqual((), self.checked(extra=("--leave-other-staged",)))

    def test_a_repository_that_selects_a_program(self):
        self.git("config", "core.fsmonitor", "some-program")
        self.assertIn("repo_config_safe", self.checked())

    def test_a_refused_path(self):
        self.assertIn("paths_valid", self.checked("/etc/hosts"))
        self.assertIn("paths_valid", self.checked("nothing-here.txt"))

    def test_a_refused_message(self):
        self.assertIn("message_valid", self.checked(subject=""))

    def test_a_credential_file_name(self):
        self.write(".env", "x=1\n")
        self.assertEqual(("paths_not_credentials",), self.checked(".env"))
        os.makedirs(os.path.join(self.dir, ".ssh"))
        self.write(".ssh/config", "host\n")
        self.assertEqual(("paths_not_credentials",), self.checked(".ssh/config"))

    def test_a_binary_path(self):
        self.write("blob.bin", b"\x00\x01\x02")
        self.assertEqual(("facts_complete",), self.checked("blob.bin"))

    def test_a_secret_in_the_diff(self):
        self.write("a.txt", "two\n" + AWS + "\n")
        self.assertEqual(("no_secret_lines",), self.checked())

    def test_a_secret_in_a_new_file_of_a_lock_file_name_is_seen_by_a_pattern_and_not_by_entropy(self):
        self.write("package-lock.json", RANDOM + "\n")
        self.assertEqual((), self.checked("package-lock.json"))
        self.write("package-lock.json", RANDOM + "\n" + AWS + "\n")
        self.assertEqual(("no_secret_lines",), self.checked("package-lock.json"))

    def test_a_secret_in_the_subject(self):
        self.assertEqual(("no_secret_lines",), self.checked(subject="Add " + GITHUB))

    def test_a_secret_in_the_body_or_a_trailer(self):
        self.assertEqual(("no_secret_lines",), self.checked(extra=("--body", "see " + KEY)))
        self.assertEqual(("no_secret_lines",), self.checked(extra=("--trailer", "Key: " + URL)))

    def test_a_secret_in_a_test_directory_diff_that_only_a_generic_pattern_finds_is_relaxed(self):
        os.makedirs(os.path.join(self.dir, "tests"))
        self.write("tests/fixture.py", LOGIN + "\n")
        self.assertEqual((), self.checked("tests/fixture.py"))
