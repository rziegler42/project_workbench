"""`safe-git describe push`, increment F (plan `2026-10-26-safe-git-describe-push`; `docs/specs/safe-git.md`, "Resolution
and the remote" and "Facts of `describe push`"): what an adversarial review of the action found.

A key of the repository's own configuration that redirects, intercepts or routes the credentials of a push is refused
and named, never its value or its host; the scan for credentials reads every added line, whatever the configuration
says about context; a NUL in a commit message is not read past; a pattern for a token takes time in proportion to the
text; an error does not repeat what git printed; a name that is not a remote name is not one."""

import json
import os
import subprocess
import time
import unittest
import unittest.mock

import support_git
from support_git import git, needs_git
import test_safegit_describe_push as base

H = base.H
SECRET = "AKIA" + "ABCDEFGHIJKLMNOP"      # the shape of an AWS access key id, written in two pieces
HOSTILE = (
    ("http.curloptResolve", "example.invalid:443:192.0.2.1"), ("http.sslVerify", "false"),
    ("http.sslCert", "x.pem"), ("http.cookieFile", "cookies"), ("http.extraHeader", "X-Probe: 1"),
    ("http.followRedirects", "true"), ("protocol.ext.allow", "always"), ("credential.username", "someone"),
    ("transfer.credentialsInUrl", "allow"), ("url.https://evil.invalid/.insteadOf", "https://example.invalid/"),
    ("url.https://evil.invalid/.pushInsteadOf", "https://example.invalid/"),
    ("http.https://example.invalid/.sslVerify", "false"),
    ("remote.origin.pushurl", "https://evil.invalid/repo.git"),
)


@needs_git
class Redirects(base.Push):
    def test_each_key_that_redirects_or_intercepts_is_refused_and_named_without_its_value(self):
        for key, value in HOSTILE:
            with self.subTest(key=key):
                self.config(key, value)
                built = self.refused("push_config_refused")
                message = built["errors"][0]["message"]
                self.assertIn("local:", message)
                for piece in ("evil.invalid", "example.invalid", "192.0.2.1", "someone", "X-Probe", "cookies"):
                    self.assertNotIn(piece, json.dumps(built), key)
                git(self.repo, "config", "--unset-all", key)

    def test_the_same_keys_in_the_owners_configuration_are_named_and_the_push_is_described(self):
        self.global_config("[http]\n\tsslVerify = false\n\textraHeader = X-Probe: 1\n[url \"https://evil.invalid/\"]\n"
                           "\tinsteadOf = https://example.invalid/\n[transfer]\n\tcredentialsInUrl = allow\n")
        built = self.describe()
        self.assertEqual([], built["errors"])
        mine = self.own(built["facts"]["push_config_findings"])
        for name in ("http.sslverify", "http.extraheader", "url.*.insteadof", "transfer.credentialsinurl"):
            self.assertIn("global:" + name, mine)
        self.assertNotIn("evil.invalid", json.dumps(built))

    def test_a_key_of_a_section_this_check_does_not_name_is_not_a_finding(self):
        self.config("core.editor", "vi")
        self.config("push.autoSetupRemote", "true")
        self.assertEqual([], self.own(self.describe()["facts"]["push_config_findings"]))


@needs_git
class Scan(base.Push):
    def lines(self, *edits):
        return "\n".join(edits) + "\n"

    def test_a_secret_added_and_taken_out_again_is_found_whatever_the_context_setting(self):
        self.config("diff.interHunkContext", "20")
        plain = ["l%d" % number for number in range(1, 13)]
        self.commit("s.txt", "\n".join(plain) + "\n")
        changed = list(plain)
        changed[1] = "changed"
        changed.insert(9, SECRET)           # line 10
        self.commit("s.txt", "\n".join(changed) + "\n")
        self.commit("s.txt", "\n".join(plain[:1] + ["changed"] + plain[2:]) + "\n")
        facts = self.describe()["facts"]
        self.assertIn("aws-access-key-id 10 s.txt", facts["findings"])
        self.assertNotIn(SECRET, facts["diff"])      # the net change holds none, so the commit by commit read is the one that sees it


@needs_git
class Messages(base.Push):
    def outcome(self):
        """The object `describe push` prints, whether or not a fact was left out of it."""
        code, text, err = self.call()
        self.assertEqual((0, ""), (code, err), text)
        return json.loads(text)

    def raw_commit(self, message):
        head = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        tree = git(self.repo, "rev-parse", "HEAD^{tree}").stdout.strip()
        body = ("tree %s\nparent %s\nauthor t <t@example.invalid> 1 +0000\ncommitter t <t@example.invalid> 1 +0000\n\n"
                % (tree, head)).encode() + message
        made = subprocess.run([support_git.REAL_GIT, "hash-object", "-t", "commit", "-w", "--literally", "--stdin"],
                              cwd=self.repo, env=dict(support_git._CLEAN, HOME=self.scratch), input=body,
                              capture_output=True)
        self.assertEqual(0, made.returncode, made.stderr)
        git(self.repo, "update-ref", "refs/heads/feature", made.stdout.decode().strip())

    def test_a_nul_in_a_message_leaves_the_commit_facts_out(self):
        self.raw_commit(b"visible subject\0hidden after the nul\n")
        built = self.outcome()
        self.assertEqual(["commit_hashes", "commit_messages"], built["facts"]["omitted"])
        self.assertTrue(built["truncated"])
        self.assertNotIn("hidden", json.dumps(built))

    def test_a_forged_record_after_a_nul_is_not_read_as_a_commit(self):
        self.raw_commit(b"x\0" + b"a" * 40 + b"\nforged message\0")
        built = self.outcome()
        self.assertEqual(["commit_hashes", "commit_messages"], built["facts"]["omitted"])

    def test_a_message_without_a_nul_is_still_given(self):
        self.commit("new.txt", "one\n", message="plain message")
        facts = self.describe()["facts"]
        self.assertEqual(["plain message\n"], facts["commit_messages"])
        self.assertEqual([], facts["omitted"])

    def test_the_commit_object_may_be_read_in_one_form_only(self):
        self.assertTrue(H.git_shape_ok(["git", "cat-file", "commit", "a" * 40]))
        for argv in (["cat-file", "commit", "HEAD"], ["cat-file", "commit", "a" * 40, "b" * 40], ["cat-file", "commit"],
                     ["cat-file", "tag", "a" * 40], ["cat-file", "-p", "a" * 40], ["cat-file", "commit", "-" + "a" * 39],
                     ["cat-file", "commit", "A" * 40], ["cat-file", "--batch"]):
            self.assertFalse(H.git_shape_ok(["git"] + argv), argv)


class Shapes(unittest.TestCase):
    def test_a_patch_with_no_context_between_hunks_is_allowed_with_the_new_flag(self):
        patch = ["diff", "--no-ext-diff", "--no-textconv", "--no-renames", "--no-color", "-U0", "--text",
                 "--ignore-submodules=all", "--inter-hunk-context=0", "--src-prefix=a/", "--dst-prefix=b/"]
        self.assertTrue(H.git_shape_ok(["git"] + patch + ["a" * 40 + "..HEAD"]))
        log = ["log", "--no-merges", "-p", "--format=", "--no-show-signature", "--no-ext-diff", "--no-textconv",
               "--ignore-submodules=all", "--inter-hunk-context=0", "--no-renames", "--no-color", "-U0", "--text",
               "--src-prefix=a/", "--dst-prefix=b/"]
        self.assertTrue(H.git_shape_ok(["git"] + log + ["a" * 40 + "..HEAD"]))
        self.assertFalse(H.git_shape_ok(["git"] + patch[:8] + ["--inter-hunk-context=5"] + patch[9:] + ["a" * 40 + "..HEAD"]))


class Environment(unittest.TestCase):
    def test_git_never_writes_for_the_sake_of_a_read(self):
        self.assertEqual("0", H.git_environment(["/usr/bin"])["GIT_OPTIONAL_LOCKS"])


class Records(unittest.TestCase):
    def test_a_record_that_is_not_a_hash_and_a_message_is_left_out_before_anything_is_run(self):
        calls = []

        def fake(argv, cwd, limit, timeout=None, separator="\n"):
            calls.append(argv)
            return "not a hash\0", False
        with unittest.mock.patch.object(H, "run_capped", fake):
            self.assertEqual((H.OMIT, H.OMIT), H.range_commits("/nowhere", "a" * 40 + "..HEAD", 1))
        self.assertEqual(1, len(calls))      # the log; no commit object was asked for


class Timing(unittest.TestCase):
    def test_a_long_run_of_a_token_prefix_takes_time_in_proportion_to_its_length(self):
        text = "+" + "eyJ" * 40000 + "\n"
        patch = "diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -0,0 +1 @@\n" + text
        started = time.monotonic()
        H.scan_patch(patch, 100)
        self.assertLess(time.monotonic() - started, 2.0)

    def test_a_token_is_still_found(self):
        token = "eyJ" + "a" * 30 + "."
        patch = "diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -0,0 +1 @@\n+" + token + "\n"
        self.assertEqual([{"path": "x", "line": 1, "rule": "jwt-shaped"}], H.scan_patch(patch, 100)[0])


@needs_git
class Errors(base.Push):
    def test_a_deadline_with_no_timeout_given_is_a_refusal_not_a_type_error(self):
        self.commit("new.txt", "one\n")
        fifo = os.path.join(self.scratch, "order")
        os.mkfifo(fifo)                                   # nothing writes to it, so git waits for it
        self.config("diff.orderFile", fifo)
        argv = ["git", "diff", "--raw", "-z", "--no-renames", "--no-ext-diff", "--no-textconv",
                "--ignore-submodules=none", self.first + "..HEAD"]
        saved = H.GIT_TIMEOUT
        H.GIT_TIMEOUT = 1
        try:
            with self.assertRaises(H.Refused) as caught:
                H.run_capped(argv, self.repo, 1000)
        except TypeError:
            self.fail("a TypeError")
        finally:
            H.GIT_TIMEOUT = saved
        self.assertIn("did not finish", str(caught.exception))


@needs_git
class Echo(base.Push):
    def test_what_git_printed_is_not_repeated(self):
        self.config("core.bare", "SEKRET-VALUE-0123456789")
        code, text, err = self.call()
        self.assertEqual("", err)
        self.assertNotIn("SEKRET", text)
        self.assertEqual(["repository_unreadable"], [error["code"] for error in json.loads(text)["errors"]])


@needs_git
class Names(base.Push):
    def test_a_name_git_would_not_accept_as_a_remote_is_not_one(self):
        for name in ("a..b", "x.lock", "x.", "a.lock", "..x"):
            with self.subTest(name=name):
                self.assertIsNone(H._REMOTE_NAME.match(name), name)
        for name in ("origin", "a.b", "up-stream", "x_y", "v1.2", "lockx"):
            self.assertIsNotNone(H._REMOTE_NAME.match(name), name)

    def test_a_configured_pushremote_that_is_not_a_name_is_unresolved_with_an_object(self):
        for name in ("a..b", "x.lock"):
            with self.subTest(name=name):
                self.config("branch.feature.pushRemote", name)
                self.refused("target_unresolved")
                git(self.repo, "config", "--unset", "branch.feature.pushRemote")


if __name__ == "__main__":
    unittest.main()
