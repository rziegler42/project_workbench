"""`safe-git describe push`, increment B (plan `2026-10-26-safe-git-describe-push`; `docs/specs/safe-git.md`,
"`describe push`"): the parser of the push arguments, the repository and branch checks, and the scalar facts.

Real repositories, real git, no network and no push. A refusal is data with its code and exit status 0; every call is
checked by what it leaves behind: the repository is byte for byte the same. The later facts (the remote's transport,
the configuration, the target, the outgoing commits and the diff) belong to increments C to E and are empty or null."""

import io
import json
import os
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
LATER = {"remote_scheme": None, "remote_url_has_credentials": None, "push_config_findings": [], "push_updates": [],
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


@needs_git
class Push(support_git.Repo):
    def setUp(self):
        super().setUp()
        self.main = git(self.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        self.first = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        git(self.repo, "update-ref", "refs/remotes/origin/" + self.main, self.first)
        git(self.repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/" + self.main)
        git(self.repo, "switch", "-q", "-c", "feature")

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
        git(self.repo, "update-ref", "refs/remotes/mine/feature", self.first)
        self.config("remote.pushDefault", "mine")
        self.config("user.motd", "first line\nremote.pushDefault=origin")
        self.assertEqual("mine", self.describe()["facts"]["remote"])

    def test_force_with_lease_may_join_a_force_flag(self):
        self.assertTrue(self.describe("-f", "--force-with-lease")["facts"]["force"])

    def test_a_dotted_branch_name_reads_its_own_settings(self):
        git(self.repo, "switch", "-q", "-c", "release/1.2")
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
        self.refused("base_unresolved", "backup")

    def test_the_source_may_be_named_three_ways_and_no_other(self):
        for source in ("HEAD", "feature", "refs/heads/feature"):
            self.assertTrue(self.describe("origin", "%s:other" % source)["ok"], source)
        self.refused("usage", "origin", "%s:other" % self.main)
        self.refused("usage", "origin", "refs/heads/%s:other" % self.main)
        self.refused("usage", "origin", "refs/tags/v1:other")


if __name__ == "__main__":
    unittest.main()
