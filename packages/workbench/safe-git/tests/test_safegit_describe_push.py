"""`safe-git describe push`, increment B (plan `2026-10-26-safe-git-describe-push`; `docs/specs/safe-git.md`,
"`describe push`"): the parser of the push arguments, the repository and branch checks, and the scalar facts.

Real repositories, real git, no network and no push. A refusal is data with its code and exit status 0; every call is
checked by what it leaves behind: the repository is byte for byte the same. The later facts (the remote's transport,
the configuration, the target, the outgoing commits and the diff) belong to increments C to E and are empty or null."""

import io
import json
import os
import subprocess
import unittest
import unittest.mock

from tests import support_helpers

import support_git
from support_git import git, needs_git
from test_safegit_describe_remove import snapshot

H = support_helpers.load("safe-git")
STANDARD = "/usr/bin" + os.pathsep + "/bin" + os.pathsep + "/usr/local/bin" + os.pathsep + "/opt/homebrew/bin"
FACTS = ("head", "branch", "remote", "default_branch", "force", "delete", "set_upstream", "no_verify", "dry_run",
         "atomic", "remote_scheme", "remote_url_has_credentials", "push_config_findings", "push_updates",
         "push_deletes", "push_forced", "base", "ahead", "tracking_ref_reflog_looks_git_written", "commit_hashes",
         "commit_messages", "changed_paths", "binary_paths", "submodule_paths", "findings", "diff")
FLAGS = ("force", "delete", "set_upstream", "no_verify", "dry_run", "atomic")
LATER = {"push_updates": [],
         "push_deletes": [], "push_forced": [], "tracking_ref_reflog_looks_git_written": None, "commit_hashes": [],
         "commit_messages": [], "changed_paths": [], "binary_paths": [], "submodule_paths": [], "findings": [],
         "diff": None}
CREDENTIAL = "hunter2-not-a-real-password"


class Shapes(unittest.TestCase):
    def test_the_config_listing_with_scopes_is_accepted(self):
        self.assertTrue(H.git_shape_ok(["git", "config", "--list", "--show-scope", "-z"]))

    def test_other_config_shapes_are_refused(self):
        for rest in (["--list", "--show-scope"], ["--show-scope", "--list", "-z"], ["--list", "-z", "--show-scope"],
                     ["--list", "--show-scope", "-z", "--file", "x"], ["--get", "remote.origin.url"],
                     ["--list", "--show-origin", "-z"], ["--global", "--list", "-z"]):
            self.assertFalse(H.git_shape_ok(["git", "config"] + rest), rest)


class RemoteShape(unittest.TestCase):
    def test_the_push_url_read_of_a_remote_name_is_accepted(self):
        for name in ("origin", "a", "my-remote_1.x", "a" * 64):
            self.assertTrue(H.git_shape_ok(["git", "remote", "get-url", "--push", "--all", name]), name)

    def test_any_other_remote_shape_is_refused(self):
        for rest in (["get-url", "--push", "--all", "-x"], ["get-url", "--push", "--all", "a" * 65],
                     ["get-url", "--push", "--all", "https://example.invalid/x"], ["get-url", "--push", "--all"],
                     ["get-url", "--push", "--all", "a", "b"], ["get-url", "--push", "a"], ["get-url", "--all", "a"],
                     ["get-url", "a"], ["--push", "get-url", "--all", "a"], ["add", "a", "https://example.invalid/x"],
                     ["remove", "a"], ["update"], ["show", "origin"], ["set-url", "a", "x"],
                     ["get-url", "--push", "--all", "a\n"], ["get-url", "--push", "--all", ""]):
            self.assertFalse(H.git_shape_ok(["git", "remote"] + rest), rest)


@needs_git
class Push(support_git.Repo):
    def setUp(self):
        super().setUp()
        self.main = git(self.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        self.first = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        git(self.repo, "update-ref", "refs/remotes/origin/" + self.main, self.first)
        git(self.repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/" + self.main)
        git(self.repo, "switch", "-q", "-c", "feature")
        self.remote("origin", "https://example.invalid/repo.git")

    @staticmethod
    def own(findings):
        """The findings of the scopes a test controls. The machine's system configuration is not the test's, and it may
        name a credential helper of its own."""
        return [item for item in findings if item.partition(":")[0] in ("global", "local", "worktree")]

    def remote(self, name, url):
        git(self.repo, "remote", "add", name, url)

    def global_config(self, text):
        """Write the owner's global configuration, which the helper reads as `HOME/.gitconfig`."""
        with open(os.path.join(self.scratch, ".gitconfig"), "w") as handle:
            handle.write(text)

    def commit(self, rel, data, message="change"):
        self.write(rel, data)
        git(self.repo, "add", "--", rel)
        git(self.repo, "commit", "-q", "-m", message)
        return git(self.repo, "rev-parse", "HEAD").stdout.strip()

    def call(self, *args, cwd=None, path=None):
        out, err = io.StringIO(), io.StringIO()
        with unittest.mock.patch.dict(os.environ, {"PATH": path or STANDARD, "HOME": self.scratch}, clear=True):
            code = H.main(["describe", "push"] + list(args), out, err, cwd or self.repo)
        return code, out.getvalue(), err.getvalue()

    def describe(self, *args, **more):
        """The object `describe push <args>` prints, with the repository checked to be unchanged."""
        before = snapshot(self.repo)
        code, text, err = self.call(*args, **more)
        self.assertEqual((0, ""), (code, err), text)
        self.assertEqual(1, text.count("\n"))
        built = json.loads(text)
        self.assertEqual(["contract", "action", "ok", "truncated", "errors", "facts"], list(built))
        self.assertEqual((1, "push"), (built["contract"], built["action"]))
        self.assertEqual(list(FACTS) + ["omitted"], list(built["facts"]))
        self.assertEqual(before, snapshot(self.repo))
        return built

    def refused(self, code, *args, **more):
        built = self.describe(*args, **more)
        self.assertEqual([code], [error["code"] for error in built["errors"]], built)
        self.assertFalse(built["ok"])
        self.assertTrue(0 < len(built["errors"][0]["message"]) <= 500)
        return built


class Facts(Push):
    def test_a_plain_push_of_the_current_branch(self):
        head = self.commit("b.txt", "two\n")
        facts = self.describe()["facts"]
        self.assertEqual((head, "feature", "origin", self.main), (facts["head"], facts["branch"], facts["remote"],
                                                                  facts["default_branch"]))
        self.assertEqual([False] * len(FLAGS), [facts[name] for name in FLAGS])
        self.assertEqual((self.first, 1), (facts["base"], facts["ahead"]))
        self.assertEqual(("https", False, []), (facts["remote_scheme"], facts["remote_url_has_credentials"],
                                                self.own(facts["push_config_findings"])))
        for name, value in LATER.items():
            self.assertEqual(value, facts[name], name)
        built = self.describe()
        self.assertTrue(built["ok"])
        self.assertEqual([], built["errors"])

    def test_the_base_is_the_tracking_ref_of_the_branch_when_there_is_one(self):
        middle = self.commit("b.txt", "two\n")
        git(self.repo, "update-ref", "refs/remotes/origin/feature", middle)
        self.commit("c.txt", "three\n")
        facts = self.describe()["facts"]
        self.assertEqual((middle, 1), (facts["base"], facts["ahead"]))

    def test_a_branch_with_no_new_commit_is_ahead_by_none(self):
        facts = self.describe()["facts"]
        self.assertEqual((self.first, 0), (facts["base"], facts["ahead"]))

    def test_each_flag_is_a_fact(self):
        self.commit("b.txt", "two\n")
        for args, name in ((["-f"], "force"), (["--force"], "force"), (["--force-with-lease"], "force"),
                           (["-u"], "set_upstream"), (["--set-upstream"], "set_upstream"),
                           (["--no-verify"], "no_verify"), (["-n"], "dry_run"), (["--dry-run"], "dry_run"),
                           (["--atomic"], "atomic")):
            facts = self.describe(*args)["facts"]
            self.assertEqual([name], [flag for flag in FLAGS if facts[flag]], args)

    def test_delete_is_a_fact_and_gives_no_range(self):
        self.commit("b.txt", "two\n")
        for args in (["--delete", "origin", "other"], ["-d", "origin", "other"], ["origin", ":other"],
                     ["origin", ":other", ":another"]):
            facts = self.describe(*args)["facts"]
            self.assertEqual((None, 0), (facts["base"], facts["ahead"]), args)
        self.assertTrue(self.describe("-d", "origin", "other")["facts"]["delete"])
        self.assertFalse(self.describe("origin", ":other")["facts"]["delete"])

    def test_quiet_and_verbose_are_accepted(self):
        for args in (["-q"], ["--quiet"], ["-v"], ["--verbose"], ["-q", "-v"]):
            self.assertTrue(self.describe(*args)["ok"], args)

    def test_a_remote_and_a_refspec_of_the_current_branch(self):
        self.commit("b.txt", "two\n")
        for args in (["origin"], ["origin", "feature"], ["origin", "HEAD"], ["origin", "refs/heads/feature"],
                     ["origin", "HEAD:feature"], ["origin", "+feature:refs/heads/other"], ["-f", "origin", "HEAD:other"]):
            built = self.describe(*args)
            self.assertTrue(built["ok"], (args, built["errors"]))
            self.assertEqual("origin", built["facts"]["remote"])

    def test_a_flag_after_the_remote_is_usage(self):
        self.refused("usage", "origin", "-f")

    def test_the_remote_is_the_one_git_would_use(self):
        self.commit("b.txt", "two\n")
        for name in ("backup", "mine", "other"):
            self.remote(name, "https://example.invalid/%s.git" % name)
            git(self.repo, "update-ref", "refs/remotes/%s/feature" % name, self.first)
        self.assertEqual("origin", self.describe()["facts"]["remote"])
        self.config("branch.feature.remote", "backup")
        self.assertEqual("backup", self.describe()["facts"]["remote"])
        self.config("remote.pushDefault", "mine")
        self.assertEqual("mine", self.describe()["facts"]["remote"])
        self.config("branch.feature.pushRemote", "other")
        self.assertEqual("other", self.describe()["facts"]["remote"])
        self.assertEqual("backup", self.describe("backup")["facts"]["remote"])

    def test_a_remote_setting_that_is_not_a_name_is_unresolved(self):
        self.config("branch.feature.pushRemote", "https://example.invalid/x.git")
        built = self.refused("target_unresolved")
        self.assertNotIn("example.invalid", json.dumps(built))

    def test_a_remote_setting_with_no_value_is_unresolved(self):
        with open(os.path.join(self.repo, ".git", "config"), "a") as handle:
            handle.write('[branch "feature"]\n\tpushRemote\n')
        self.refused("target_unresolved")

    def test_a_setting_with_a_newline_in_its_value_is_read_whole(self):
        self.remote("mine", "https://example.invalid/mine.git")
        git(self.repo, "update-ref", "refs/remotes/mine/feature", self.first)
        self.config("remote.pushDefault", "mine")
        self.config("user.motd", "first line\nremote.pushDefault=origin")
        self.assertEqual("mine", self.describe()["facts"]["remote"])

    def test_force_with_lease_may_join_a_force_flag(self):
        self.assertTrue(self.describe("-f", "--force-with-lease")["facts"]["force"])

    def test_a_dotted_branch_name_reads_its_own_settings(self):
        git(self.repo, "switch", "-q", "-c", "release/1.2")
        self.remote("mine", "https://example.invalid/mine.git")
        git(self.repo, "update-ref", "refs/remotes/mine/release/1.2", self.first)
        self.config("branch.release/1.2.pushRemote", "mine")
        self.assertEqual("mine", self.describe()["facts"]["remote"])

    def test_a_tracking_ref_that_is_missing_falls_back_to_the_default_branch(self):
        facts = self.describe()["facts"]
        self.assertEqual(self.first, facts["base"])

    def test_the_default_branch_is_null_without_the_remote_head(self):
        git(self.repo, "symbolic-ref", "--delete", "refs/remotes/origin/HEAD")
        git(self.repo, "update-ref", "refs/remotes/origin/feature", self.first)
        facts = self.describe()["facts"]
        self.assertEqual((None, self.first), (facts["default_branch"], facts["base"]))


class Usage(Push):
    def test_usage(self):
        for args in (["-fu"], ["-f", "-f"], ["-f", "--force"], ["--force-with-lease=feature"], ["--all"], ["--tags"],
                     ["--prune"], ["--repo=x"], ["--repo", "x"], ["-o", "x"], ["--push-option=x"],
                     ["--receive-pack=x"], ["--exec=x"], ["--signed"], ["--signed=if-asked"],
                     ["--recurse-submodules=check"], ["--porcelain"], ["--force-if-includes"], ["--no-such-flag"],
                     ["-x"], ["--"], ["-"], [""], ["--dry-run=1"], ["-q", "-q"],
                     ["https://example.invalid/x.git"], ["ssh://git@example.invalid/x.git"], ["/tmp/some/repo"],
                     ["../elsewhere"], ["git@example.invalid:x/y.git"], ["bad name"], ["a" * 65],
                     ["origin", "^feature"], ["origin", "a:b:c"], ["origin", ":"], ["origin", "+"],
                     ["origin", "+:feature"], ["origin", "feature", "feature"], ["origin", "HEAD:a", "HEAD:b"],
                     ["origin", "other"], ["origin", "other:feature"], ["origin", "v1.0:v1.0"],
                     ["origin", "feature:refs/heads/a..b"], ["origin", "feature:a//b"], ["origin", "feature:a/"],
                     ["origin", "feature:a.lock"], ["origin", "fe ature"], ["origin", "feature:"],
                     ["origin", "-x"], ["origin", "feature", "--force"], ["origin", ":a:b"], ["origin", ""],
                     ["--delete"], ["-d"], ["--delete", "origin"], ["--delete", "origin", "a:b"],
                     ["--delete", "origin", "HEAD:a"], ["--delete", "origin", "+a"], ["-d", "-d", "origin", "a"],
                     ["origin", "HEAD:a", ":b"], ["--delete", "origin", ":b"]):
            built = self.refused("usage", *args)
            facts = built["facts"]
            self.assertEqual([False] * len(FLAGS), [facts[name] for name in FLAGS], args)
            self.assertEqual([None, None, None, None], [facts[n] for n in ("head", "branch", "remote", "base")], args)
            self.assertEqual(None, facts["ahead"])

    def test_the_remote_and_state_dependent_forms_have_their_own_code(self):
        for args in (["--mirror"], ["--follow-tags"], ["origin", "refs/heads/*:refs/heads/*"],
                     ["origin", "feature*"], ["origin", "*:*"]):
            self.refused("remote_state_required", *args)

    def test_no_message_quotes_an_argument(self):
        for secret in ("https://user:%s@example.invalid/x.git" % CREDENTIAL, "--token=%s" % CREDENTIAL):
            code, text, err = self.call(secret)
            self.assertNotIn(CREDENTIAL, text + err)
        for refspec in ("%s:feature" % CREDENTIAL, "feature:%s" % CREDENTIAL, "+%s" % CREDENTIAL):
            code, text, err = self.call("origin", refspec)
            self.assertNotIn(CREDENTIAL, text + err)

    def test_an_unknown_action_is_still_refused_with_no_object(self):
        out, err = io.StringIO(), io.StringIO()
        self.assertEqual(1, H.main(["describe", "frob"], out, err, self.repo))
        self.assertEqual("", out.getvalue())
        self.assertIn("push", err.getvalue())


class Repository(Push):
    def test_no_repository(self):
        self.refused("repository_unreadable", cwd=self.outside)

    def test_a_branch_with_no_commit(self):
        empty = os.path.join(self.scratch, "empty")
        os.mkdir(empty)
        git(empty, "init", "-q")
        before = snapshot(empty)
        code, text, err = self.call(cwd=empty)
        self.assertEqual((0, ""), (code, err))
        built = json.loads(text)
        self.assertEqual(["branch_unborn"], [error["code"] for error in built["errors"]])
        self.assertEqual(before, snapshot(empty))

    def test_a_detached_head(self):
        git(self.repo, "switch", "-q", "--detach")
        built = self.refused("head_detached")
        self.assertEqual(self.first, built["facts"]["head"])
        self.assertIsNone(built["facts"]["branch"])

    def test_a_branch_name_the_helper_does_not_read(self):
        git(self.repo, "switch", "-q", "-c", "featé")
        self.refused("branch_unreadable")

    def test_a_repository_that_selects_a_program(self):
        hook = self.write(".git/hooks/pre-push", "#!/bin/sh\nexit 0\n", mode=0o755)
        built = self.refused("repo_selects_program")
        self.assertIn("hook:pre-push", built["errors"][0]["message"])
        os.remove(hook)
        self.config("core.fsmonitor", "/bin/true")
        self.refused("repo_selects_program")

    def test_an_unborn_branch_with_a_name_the_helper_does_not_read(self):
        empty = os.path.join(self.scratch, "empty")
        os.mkdir(empty)
        git(empty, "init", "-q")
        git(empty, "symbolic-ref", "HEAD", "refs/heads/feat\u00e9")
        code, text, err = self.call(cwd=empty)
        self.assertEqual((0, ""), (code, err))
        self.assertEqual(["branch_unreadable"], [error["code"] for error in json.loads(text)["errors"]])

    def test_a_long_token_in_a_subsection_is_not_kept(self):
        token = "github" + "_pat_" + "A1b2C3d4E5" * 12      # 120 characters, no dot: longer than the cut of a finding
        git(self.repo, "config", "credential.https://oauth2:%s@example.invalid.helper" % token, "store")
        code, text, err = self.call()
        self.assertEqual((0, ""), (code, err))
        built = json.loads(text)
        self.assertEqual(["repo_selects_program"], [error["code"] for error in built["errors"]])
        self.assertIn("credential.*.helper", built["errors"][0]["message"])
        for piece in ("A1b2C3d4", "oauth2", "example.invalid", "pat_"):
            self.assertNotIn(piece, text)

    def test_a_program_setting_with_a_subsection_is_named_without_it(self):
        url = "https://user:%s@example.invalid" % CREDENTIAL
        git(self.repo, "config", "credential.%s.helper" % url, "store")
        code, text, err = self.call()
        self.assertEqual((0, ""), (code, err))
        built = json.loads(text)
        self.assertEqual(["repo_selects_program"], [error["code"] for error in built["errors"]])
        self.assertIn("credential.*.helper", built["errors"][0]["message"])
        self.assertNotIn(CREDENTIAL, text)
        self.assertNotIn("example.invalid", text)

    def test_no_base(self):
        git(self.repo, "update-ref", "-d", "refs/remotes/origin/" + self.main)
        git(self.repo, "symbolic-ref", "--delete", "refs/remotes/origin/HEAD")
        self.refused("base_unresolved")

    def test_a_remote_with_no_tracking_ref_has_no_base(self):
        self.remote("backup", "https://example.invalid/backup.git")
        self.refused("base_unresolved", "backup")

    def test_the_source_may_be_named_three_ways_and_no_other(self):
        for source in ("HEAD", "feature", "refs/heads/feature"):
            self.assertTrue(self.describe("origin", "%s:other" % source)["ok"], source)
        self.refused("usage", "origin", "%s:other" % self.main)
        self.refused("usage", "origin", "refs/heads/%s:other" % self.main)
        self.refused("usage", "origin", "refs/tags/v1:other")


SCHEMES = (("https://example.invalid/x.git", "https"), ("http://example.invalid/x.git", "http"),
           ("HTTPS://example.invalid/x.git", "https"),
           ("ssh://git@example.invalid/x.git", "ssh"), ("git@example.invalid:x/y.git", "ssh"),
           ("example.invalid:x/y.git", "ssh"), ("git://example.invalid/x.git", "git"),
           ("file:///srv/x.git", "file"), ("/srv/x.git", "file"), ("../x.git", "file"), ("./a:b/x.git", "file"),
           ("ftp://example.invalid/x.git", "other"), ("foo://example.invalid/x.git", "other"),
           ("git+ssh://example.invalid/x.git", "other"))
TOKEN = "gh" + "p_" + "abcdefghijklmnopqrst"   # in pieces, as in the push-check tests


class Transport(Push):
    def url(self, url, name="origin"):
        git(self.repo, "config", "remote.%s.url" % name, url)

    def facts(self, *args):
        built = self.describe(*args)
        self.assertEqual([], built["errors"], built)
        return built["facts"]

    def test_the_scheme_of_each_kind_of_url(self):
        for url, scheme in SCHEMES:
            self.url(url)
            facts = self.facts()
            self.assertEqual((scheme, False), (facts["remote_scheme"], facts["remote_url_has_credentials"]), url)

    def test_a_credential_in_the_url(self):
        for url, scheme, has in (("https://user:%s@example.invalid/x.git" % CREDENTIAL, "https", True),
                                 ("https://user@example.invalid/x.git", "https", True),
                                 ("http://%s@example.invalid/x.git" % TOKEN, "http", True),
                                 ("ssh://git:%s@example.invalid/x.git" % CREDENTIAL, "ssh", True),
                                 ("ssh://git@example.invalid/x.git", "ssh", False),
                                 ("git://git@example.invalid/x.git", "git", False),
                                 ("ssh://%s@example.invalid/x.git" % TOKEN, "ssh", True),
                                 ("%s@example.invalid:x/y.git" % TOKEN, "ssh", True),
                                 ("git@example.invalid:x/y.git", "ssh", False),
                                 ("ftp://user:%s@example.invalid/x.git" % CREDENTIAL, "other", True),
                                 ("ftp://user@example.invalid/x.git", "other", True),
                                 ("https://example.invalid/x@y.git", "https", False),
                                 ("https://u:pa@ss@example.invalid/x.git", "https", True),
                                 ("http://x@y@example.invalid/x.git", "http", True),
                                 ("ssh://[::1]:22/x.git", "ssh", False),
                                 ("ssh://git@[::1]:22/x.git", "ssh", False),
                                 ("[::1]:x/y.git", "ssh", False),
                                 ("file:///srv/x.git", "file", False)):
            self.url(url)
            facts = self.facts()
            self.assertEqual((scheme, has), (facts["remote_scheme"], facts["remote_url_has_credentials"]), url)

    def test_neither_the_url_nor_a_credential_is_in_the_object(self):
        for url in ("https://user:%s@example.invalid/x.git" % CREDENTIAL, "ssh://%s@example.invalid/x.git" % TOKEN):
            self.url(url)
            code, text, err = self.call()
            self.assertEqual((0, ""), (code, err))
            for piece in (CREDENTIAL, TOKEN, "example.invalid", "user:"):
                self.assertNotIn(piece, text, url)

    def test_the_facts_follow_the_push_url(self):
        self.url("https://user:%s@example.invalid/x.git" % CREDENTIAL)
        git(self.repo, "config", "remote.origin.pushurl", "ssh://git@example.invalid/x.git")
        facts = self.facts()
        self.assertEqual(("ssh", False), (facts["remote_scheme"], facts["remote_url_has_credentials"]))
        self.url("ssh://git@example.invalid/x.git")
        git(self.repo, "config", "remote.origin.pushurl", "https://user:%s@example.invalid/x.git" % CREDENTIAL)
        facts = self.facts()
        self.assertEqual(("https", True), (facts["remote_scheme"], facts["remote_url_has_credentials"]))

    def test_a_push_instead_of_rewrite_is_followed(self):
        self.url("http://example.invalid/x.git")
        self.assertEqual("http", self.facts()["remote_scheme"])
        self.config("url.ssh://git@example.invalid/.pushInsteadOf", "http://example.invalid/")
        self.assertEqual("ssh", self.facts()["remote_scheme"])
        self.config("url.git://example.invalid/.insteadOf", "http://example.invalid/")
        self.assertEqual("ssh", self.facts()["remote_scheme"])

    def test_two_urls_and_no_push_url_are_more_than_one(self):
        git(self.repo, "config", "--add", "remote.origin.url", "https://example.invalid/other.git")
        self.refused("multiple_push_urls")

    def test_one_push_url_governs_several_urls(self):
        git(self.repo, "config", "--add", "remote.origin.url", "https://example.invalid/other.git")
        git(self.repo, "config", "remote.origin.pushurl", "ssh://git@example.invalid/x.git")
        self.assertEqual("ssh", self.facts()["remote_scheme"])

    def test_a_remote_with_a_dotted_name_and_only_a_push_url(self):
        git(self.repo, "config", "remote.my.fork.pushurl", "ssh://git@example.invalid/x.git")
        git(self.repo, "update-ref", "refs/remotes/my.fork/feature", self.first)
        self.assertEqual("ssh", self.facts("my.fork")["remote_scheme"])

    def test_a_rewrite_into_a_transport_helper_is_refused(self):
        self.url("https://example.invalid/x.git")
        self.config("url.ext::sh -c true %.pushInsteadOf", "https://example.invalid/")
        built = self.refused("repo_selects_program")
        self.assertIn("remote:helper-transport", built["errors"][0]["message"])

    def test_a_url_that_could_not_be_read_leaves_the_credential_fact_null(self):
        for args, code in ((["nosuch"], "remote_unconfigured"),):
            built = self.refused(code, *args)
            self.assertIsNone(built["facts"]["remote_url_has_credentials"])
        git(self.repo, "config", "--add", "remote.origin.pushurl", "https://example.invalid/a.git")
        git(self.repo, "config", "--add", "remote.origin.pushurl", "https://example.invalid/b.git")
        self.assertIsNone(self.refused("multiple_push_urls")["facts"]["remote_url_has_credentials"])

    def test_a_remote_with_no_url_is_unconfigured(self):
        for args in (["nosuch"], ["bare"]):
            self.config("remote.bare.fetch", "+refs/heads/*:refs/remotes/bare/*")
            built = self.refused("remote_unconfigured", *args)
            self.assertEqual(args[0], built["facts"]["remote"])
            self.assertIsNone(built["facts"]["remote_scheme"])
            self.assertIsNone(built["facts"]["base"])

    def test_the_default_remote_is_checked_too(self):
        git(self.repo, "remote", "remove", "origin")
        self.refused("remote_unconfigured")

    def test_more_than_one_push_url(self):
        git(self.repo, "config", "--add", "remote.origin.pushurl", "https://example.invalid/a.git")
        git(self.repo, "config", "--add", "remote.origin.pushurl", "https://example.invalid/b.git")
        built = self.refused("multiple_push_urls")
        self.assertNotIn("example.invalid", json.dumps(built))

    def test_a_transport_helper_is_a_program(self):
        marker = os.path.join(self.scratch, "ran")
        for url in ("ext::sh -c 'touch %s'" % marker, "ext::sh -c touch% " + marker, "foo::https://example.invalid/x",
                    "fd::17"):
            self.url(url)
            built = self.refused("repo_selects_program")
            self.assertIn("remote:helper-transport", built["errors"][0]["message"])
            self.assertNotIn(marker, json.dumps(built))
            self.assertFalse(os.path.exists(marker))
            self.assertIsNone(built["facts"]["remote_scheme"])

    def test_the_url_is_never_in_an_error_message(self):
        self.url("https://user:%s@example.invalid/x.git" % CREDENTIAL)
        git(self.repo, "update-ref", "-d", "refs/remotes/origin/" + self.main)
        git(self.repo, "symbolic-ref", "--delete", "refs/remotes/origin/HEAD")
        code, text, err = self.call()
        self.assertEqual((0, ""), (code, err))
        self.assertEqual(["base_unresolved"], [e["code"] for e in json.loads(text)["errors"]])
        self.assertNotIn(CREDENTIAL, text)
        self.assertNotIn("example.invalid", text)


NAMED = (("credential.helper", "credential.helper"), ("credential.https://user:%s@h.invalid.helper" % CREDENTIAL,
                                                       "credential.*.helper"),
         ("http.proxy", "http.proxy"), ("http.https://user:%s@h.invalid.proxy" % CREDENTIAL, "http.*.proxy"),
         ("https.proxy", "https.proxy"), ("remote.origin.proxy", "remote.*.proxy"), ("ssh.variant", "ssh.variant"),
         ("core.sshCommand", "core.sshcommand"), ("core.gitProxy", "core.gitproxy"), ("core.askPass", "core.askpass"),
         ("remote.origin.receivepack", "remote.*.receivepack"), ("remote.origin.vcs", "remote.*.vcs"),
         ("push.gpgSign", "push.gpgsign"), ("push.pushOption", "push.pushoption"),
         ("remote.origin.pushOption", "remote.*.pushoption"), ("push.recurseSubmodules", "push.recursesubmodules"),
         ("push.negotiate", "push.negotiate"))
# Settings the repository may not carry: the first group is refused as a program the repository selects, as `commit`
# does; the second redirects or intercepts the push.
REPO_PROGRAM = ("credential.helper", "core.sshCommand", "core.gitProxy", "core.askPass", "remote.origin.receivepack",
                "remote.origin.vcs", "credential.https://user:%s@h.invalid.helper" % CREDENTIAL)


class Configuration(Transport):
    def global_section(self, key, value):
        """`key = value` written into the global configuration under the section and subsection of `key`."""
        parts = key.split(".")
        section = parts[0] if len(parts) == 2 else '%s "%s"' % (parts[0], ".".join(parts[1:-1]))
        self.global_config("[%s]\n\t%s = %s\n" % (section, parts[-1], value))

    def test_a_setting_of_the_owner_is_named_and_does_not_decline(self):
        for key, name in NAMED:
            self.global_section(key, "x")
            built = self.describe()
            self.assertTrue(built["ok"], (key, built["errors"]))
            self.assertEqual(["global:" + name], self.own(built["facts"]["push_config_findings"]), key)
            self.assertNotIn(CREDENTIAL, json.dumps(built))
            self.assertNotIn("h.invalid", json.dumps(built))

    def test_a_setting_of_the_repository_is_refused(self):
        for key, name in NAMED:
            self.config(key, "x")
            built = self.describe()
            code = "repo_selects_program" if key in REPO_PROGRAM else "push_config_refused"
            self.assertEqual([code], [e["code"] for e in built["errors"]], key)
            text = json.dumps(built)
            self.assertNotIn(CREDENTIAL, text)
            self.assertNotIn("h.invalid", text)
            if code == "push_config_refused":
                self.assertIn(name, built["errors"][0]["message"])
                self.assertEqual(["local:" + name], self.own(built["facts"]["push_config_findings"]), key)
            git(self.repo, "config", "--unset", key)

    def test_findings_are_in_order_without_repeats(self):
        self.global_config("[http]\n\tproxy = x\n[credential]\n\thelper = y\n[credential \"https://a.invalid\"]\n"
                           "\thelper = z\n[credential \"https://b.invalid\"]\n\thelper = z\n")
        findings = self.own(self.describe()["facts"]["push_config_findings"])
        self.assertEqual(["global:credential.*.helper", "global:credential.helper", "global:http.proxy"], findings)

    def test_a_setting_that_is_not_named_is_not_a_finding(self):
        self.global_config("[user]\n\tname = t\n[http]\n\tsslVerify = true\n[push]\n\tdefault = current\n")
        self.assertEqual([], self.own(self.describe()["facts"]["push_config_findings"]))

    def test_no_program_a_setting_names_is_started(self):
        marker = os.path.join(self.scratch, "ran")
        script = self.write("../marker.sh", "#!/bin/sh\ntouch '%s'\n" % marker, mode=0o755)
        self.global_config("[core]\n\tsshCommand = %s\n\taskPass = %s\n\tgitProxy = %s\n[credential]\n"
                           "\thelper = !%s\n[remote \"origin\"]\n\treceivepack = %s\n\tvcs = %s\n[ssh]\n"
                           "\tvariant = ssh\n[http]\n\tproxy = http://example.invalid:9\n"
                           % ((script,) * 6))
        self.url("ssh://git@example.invalid/x.git")
        built = self.describe()
        self.assertTrue(built["ok"], built["errors"])
        self.assertFalse(os.path.exists(marker))
        # The control: the same configuration does start the program for a real transport. Without this the marker
        # staying absent would prove nothing.
        self.global_config("[core]\n\tsshCommand = %s\n" % script)   # the others would change the transport
        env = {"PATH": STANDARD, "HOME": self.scratch, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"}
        control = subprocess.run([support_git.REAL_GIT, "ls-remote", "origin"], cwd=self.repo, env=env,
                                 capture_output=True, text=True, timeout=60)
        self.assertTrue(os.path.exists(marker), "the control did not start the program: %r" % control.stderr)
        os.remove(marker)
        for key in ("core.sshCommand", "core.askPass", "core.gitProxy", "remote.origin.receivepack", "remote.origin.vcs"):
            self.config(key, script)
            self.describe()
            self.assertFalse(os.path.exists(marker), key)
            git(self.repo, "config", "--unset", key)


if __name__ == "__main__":
    unittest.main()
