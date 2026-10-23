"""The helper's `push-check` (plan `2026-10-23-push-checkpoint`, increment A).

Real git and real repositories, no network. The keys planted here are fake and are written in pieces, so this
file holds nothing a scan of the repository would flag."""

import io
import json
import os
import time
import unittest
import unittest.mock

from tests import support_helpers

import support_git
from support_git import git, needs_git

H = support_helpers.load("safe-git")
STANDARD = "/usr/bin" + os.pathsep + "/bin" + os.pathsep + "/usr/local/bin" + os.pathsep + "/opt/homebrew/bin"
HEX = "a" * 40
KEYS = {
    "private-key": "-----BEGIN RSA " + "PRIVATE KEY-----",
    "aws-access-key-id": "AK" + "IA" + "ABCDEFGHIJKLMNOP",
    "github-token": "gh" + "p_" + "abcdefghijklmnopqrst",
    "sk-key": "s" + "k-" + "abcdefghijklmnopqrst",
    "slack-token": "xo" + "xb-" + "0123456789abc",
    "jwt-shaped": "ey" + "J" + "abcdefghijklmnopqrstu" + ".",
}
ALLOWED = {"rev-parse", "symbolic-ref", "show-ref", "rev-list", "diff", "log", "ls-files", "config"}
FORBIDDEN = {"push", "fetch", "ls-remote", "pull", "clone", "checkout", "switch", "merge", "rebase", "tag",
             "branch", "commit", "add", "reset"}


class Shapes(unittest.TestCase):
    def test_the_shapes_push_check_uses_are_accepted(self):
        for argv in (["symbolic-ref", "-q", "HEAD"],
                     ["show-ref", "--verify", "--hash", "refs/remotes/origin/main"],
                     ["show-ref", "--verify", "--hash", "refs/heads/feature/x"],
                     ["symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD"],
                     ["rev-list", "--count", HEX + "..HEAD"],
                     ["diff", "--name-only", "-z", "--no-renames", "--diff-filter=d", HEX + "..HEAD"],
                     ["diff", "--no-ext-diff", "--no-textconv", "--no-renames", "--no-color", "-U0", "--text",
                      "--ignore-submodules=all", "--src-prefix=a/", "--dst-prefix=b/", HEX + "..HEAD"],
                     ["log", "--no-merges", "-p", "--format=", "--no-show-signature", "--no-ext-diff",
                      "--no-textconv", "--no-renames", "--no-color", "-U0", "--text", "--ignore-submodules=all",
                      "--src-prefix=a/", "--dst-prefix=b/", HEX + "..HEAD"]):
            self.assertTrue(H.git_shape_ok(["git", *argv]), argv)

    def test_a_ref_a_range_or_a_flag_outside_those_shapes_is_refused(self):
        for argv in (["show-ref", "--verify", "--hash", "refs/remotes/-x/main"],
                     ["show-ref", "--verify", "--hash", "refs/remotes/o/../x"],
                     ["show-ref", "--verify", "--hash", "refs/tags/v1"],
                     ["show-ref", "--verify", "--hash", "HEAD"],
                     ["show-ref", "--hash", "refs/remotes/origin/main"],
                     ["show-ref", "--verify", "--hash", "refs/remotes/origin/main", "refs/heads/x"],
                     ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
                     ["symbolic-ref", "-q", "--short", "refs/remotes/origin/main"],
                     ["symbolic-ref", "-q", "--short", "HEAD"],
                     ["rev-list", "--count", "HEAD..HEAD"],
                     ["rev-list", "--count", HEX + "...HEAD"],
                     ["rev-list", "--all"],
                     ["rev-list", "--count", HEX + "..HEAD", "--"],
                     ["rev-list", "--count", "b" * 39 + "..HEAD"],
                     ["diff", "--name-only", "-z", HEX + "..HEAD", "--no-renames"],
                     ["diff", "--no-ext-diff", "--no-textconv", "-U0", "x" * 40 + "..HEAD"],
                     ["diff", "-U0", HEX + "..HEAD"],
                     ["diff", "--ext-diff", "--no-ext-diff", "--no-textconv", HEX + "..HEAD"],
                     ["diff", "--name-only", "-z", "--output=x", HEX + "..HEAD"],
                     ["diff", "--no-ext-diff", "--no-textconv", "--src-prefix=/etc/", HEX + "..HEAD"],
                     ["diff", "--name-only", "-z", "--diff-filter=D", HEX + "..HEAD"],
                     ["rev-parse", "--abbrev-ref", "HEAD"],
                     ["symbolic-ref", "-q", "refs/heads/main"], ["symbolic-ref", "HEAD"],
                     ["log", "--no-merges", "-p", "--format=", HEX + "..HEAD"],
                     ["log", "-p", "--format=", "--no-show-signature", "--no-ext-diff", "--no-textconv",
                      "--ignore-submodules=all", "--no-merges", "--output=x", HEX + "..HEAD"],
                     ["log", "--no-merges", "-p", "--format=", "--no-show-signature", "--no-ext-diff",
                      "--no-textconv", "--ignore-submodules=all", "-n", "1", HEX + "..HEAD"],
                     ["log", "--no-merges", "-p", "--format=", "--no-show-signature", "--no-ext-diff",
                      "--no-textconv", "--ignore-submodules=all", "--all", HEX + "..HEAD"],
                     ["log", "--no-merges", "-p", "--format=", "--no-show-signature", "--no-ext-diff",
                      "--no-textconv", "--ignore-submodules=all", HEX + "..HEAD", "--"]):
            self.assertFalse(H.git_shape_ok(["git", *argv]), argv)


@needs_git
class PushCheck(support_git.Repo):
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

    def check(self, *args, cwd=None, path=None):
        out, err = io.StringIO(), io.StringIO()
        with unittest.mock.patch.dict(os.environ, {"PATH": path or STANDARD, "HOME": self.scratch}, clear=True):
            code = H.main(["push-check"] + list(args), out, err, cwd or self.repo)
        return code, out.getvalue(), err.getvalue()

    def report(self, *args, **more):
        code, out, err = self.check(*args, **more)
        self.assertEqual((0, ""), (code, err), out)
        return json.loads(out)

    def assertRefused(self, result, text=None):
        code, out, err = result
        self.assertEqual((1, ""), (code, out), err)
        self.assertTrue(err.startswith("refused: "), err)
        if text:
            self.assertIn(text, err)

    def test_a_branch_with_nothing_to_send_reports_the_whole_contract_and_no_findings(self):
        report = self.report()
        self.assertEqual({"remote", "branch", "target", "default_branch", "base", "ahead", "changed_paths",
                          "findings", "truncated"}, set(report))
        self.assertEqual(("origin", "feature", "feature", self.main), (report["remote"], report["branch"],
                                                                      report["target"], report["default_branch"]))
        self.assertEqual((self.first, 0, [], [], False),
                         (report["base"], report["ahead"], report["changed_paths"], report["findings"],
                          report["truncated"]))

    def test_commits_and_changed_paths_are_counted_and_listed(self):
        self.commit("src/a.py", "print(1)\n")
        self.commit("b.txt", "two\n")
        report = self.report()
        self.assertEqual(2, report["ahead"])
        self.assertEqual(["b.txt", "src/a.py"], sorted(report["changed_paths"]))
        self.assertEqual([], report["findings"])

    def test_each_pattern_gives_one_finding_by_path_line_and_rule_and_the_text_is_never_printed(self):
        for rule, secret in KEYS.items():
            with self.subTest(rule=rule):
                git(self.repo, "reset", "-q", "--hard", self.first)
                self.commit("conf/%s.txt" % rule, "first\nsecond\nvalue = %s end\n" % secret)
                code, out, err = self.check()
                self.assertEqual((0, ""), (code, err))
                self.assertEqual([{"path": "conf/%s.txt" % rule, "line": 3, "rule": rule}],
                                 json.loads(out)["findings"])
                self.assertNotIn(secret, out)
                self.assertNotIn(secret[:8] + secret[8:14], out)

    def test_a_removed_line_and_an_unchanged_line_are_not_findings(self):
        git(self.repo, "reset", "-q", "--hard", self.first)
        self.commit("old.txt", "k = %s\n" % KEYS["aws-access-key-id"], "old")
        git(self.repo, "update-ref", "refs/remotes/origin/" + self.main, "HEAD")
        self.commit("old.txt", "k = gone\n", "remove it")
        self.assertEqual([], self.report()["findings"])

    def test_a_secret_file_name_is_a_finding_with_no_line_and_a_deleted_one_is_not(self):
        self.commit(".env", "A=1\n")
        self.commit("keys/x.pem", "x\n")
        self.commit("home/id_rsa", "x\n")
        self.commit("ok/.envrc.md", "x\n")
        found = sorted((f["path"], f["line"], f["rule"]) for f in self.report()["findings"])
        self.assertEqual([(".env", None, "secret-file-name"), ("home/id_rsa", None, "secret-file-name"),
                          ("keys/x.pem", None, "secret-file-name")], found)
        git(self.repo, "reset", "-q", "--hard", self.first)
        git(self.repo, "update-ref", "refs/remotes/origin/" + self.main, self.first)
        self.commit(".env", "A=1\n", "a")
        git(self.repo, "update-ref", "refs/remotes/origin/" + self.main, "HEAD")
        git(self.repo, "rm", "-q", ".env")
        git(self.repo, "commit", "-q", "-m", "delete")
        self.assertEqual([], self.report()["findings"])

    def test_a_path_with_a_non_ascii_name_is_read_and_printed_as_escapes(self):
        self.commit("café.txt", "k = %s\n" % KEYS["sk-key"])
        code, out, err = self.check()
        self.assertEqual((0, ""), (code, err))
        self.assertTrue(out.isascii(), out)
        found = json.loads(out)["findings"]
        self.assertEqual([("sk-key", 1)], [(f["rule"], f["line"]) for f in found])
        self.assertTrue(found[0]["path"].startswith("caf"), found)

    def test_the_base_is_the_branchs_own_tracking_ref_then_the_default_branchs_then_a_refusal(self):
        self.commit("a.txt", "x\n")
        own = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        self.assertEqual(self.first, self.report()["base"])
        git(self.repo, "update-ref", "refs/remotes/origin/feature", own)
        self.assertEqual((own, 0), (self.report()["base"], self.report()["ahead"]))
        git(self.repo, "update-ref", "-d", "refs/remotes/origin/feature")
        git(self.repo, "symbolic-ref", "--delete", "refs/remotes/origin/HEAD")
        git(self.repo, "update-ref", "-d", "refs/remotes/origin/" + self.main)
        self.assertRefused(self.check(), "refs/remotes/origin/feature")

    def test_an_unknown_default_branch_is_null_when_a_base_still_resolves(self):
        git(self.repo, "symbolic-ref", "--delete", "refs/remotes/origin/HEAD")
        git(self.repo, "update-ref", "refs/remotes/origin/feature", self.first)
        self.assertIsNone(self.report()["default_branch"])

    def test_an_explicit_base_wins_and_must_name_a_ref_that_exists(self):
        self.commit("a.txt", "x\n")
        mid = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        self.commit("b.txt", "y\n")
        git(self.repo, "update-ref", "refs/remotes/upstream/dev", mid)
        report = self.report("--base", "refs/remotes/upstream/dev")
        self.assertEqual((mid, 1, ["b.txt"]), (report["base"], report["ahead"], report["changed_paths"]))
        report = self.report("--base", "refs/heads/" + self.main)
        self.assertEqual(self.first, report["base"])
        self.assertRefused(self.check("--base", "refs/remotes/upstream/none"), "refs/remotes/upstream/none")

    def test_a_remote_other_than_origin_is_used_for_the_tracking_refs(self):
        git(self.repo, "update-ref", "refs/remotes/mirror/" + self.main, self.first)
        git(self.repo, "symbolic-ref", "refs/remotes/mirror/HEAD", "refs/remotes/mirror/" + self.main)
        self.commit("a.txt", "x\n")
        report = self.report("--remote", "mirror")
        self.assertEqual(("mirror", 1), (report["remote"], report["ahead"]))

    def test_an_argument_that_is_not_allowed_is_refused_before_git_is_asked_anything(self):
        for args in (["--remote", "-x"], ["--remote", "a/b"], ["--remote", ""], ["--remote", "a" * 100],
                     ["--remote", "a b"], ["--base", "-x"], ["--base", "HEAD"], ["--base", "refs/tags/v1"],
                     ["--base", "refs/heads/../x"], ["--base", "refs/heads/a b"], ["--base"], ["--remote"],
                     ["--force"], ["extra"], ["--base", "refs/heads/a", "--base", "refs/heads/b"],
                     ["--remote", "origin", "--remote", "mirror"]):
            with self.subTest(args=args):
                self.assertRefused(self.check(*args, path=self.recording_git()))
        self.assertEqual([], self.runs())

    def test_a_detached_head_an_unborn_branch_and_a_missing_commit_are_refused(self):
        git(self.repo, "switch", "-q", "--detach", "HEAD")
        self.assertRefused(self.check(), "detached")
        fresh = os.path.join(self.scratch, "fresh")
        os.mkdir(fresh)
        git(fresh, "init", "-q")
        self.assertRefused(self.check(cwd=fresh), "no commit")

    def test_a_repository_that_selects_a_program_is_refused_and_no_program_runs(self):
        marker = os.path.join(self.scratch, "ran")
        program = os.path.join(self.outside, "tool.sh")
        with open(program, "w") as handle:
            handle.write("#!/bin/sh\ntouch '%s'\n" % marker)
        os.chmod(program, 0o755)
        self.write(".gitattributes", "*.txt diff=x\n")
        self.commit("a.txt", "k = %s\n" % KEYS["sk-key"])
        for key in ("diff.external", "diff.x.textconv", "core.hooksPath"):
            with self.subTest(key=key):
                self.config(key, program)
                self.assertRefused(self.check(), key.lower())
                git(self.repo, "config", "--unset", key)
        self.assertFalse(os.path.exists(marker))
        self.assertEqual(1, len(self.report()["findings"]))

    def test_it_asks_git_only_read_only_things_and_never_the_network(self):
        git(self.repo, "remote", "add", "origin", os.path.join(self.scratch, "nowhere.git"))
        self.commit("a.txt", "x\n")
        self.report(path=self.recording_git())
        seen = {arguments[0] for arguments, _ in self.runs()}
        self.assertTrue(seen)
        self.assertLessEqual(seen, ALLOWED)
        self.assertFalse(seen & FORBIDDEN)

    def test_it_changes_nothing(self):
        self.commit("a.txt", "k = %s\n" % KEYS["sk-key"])
        before = (git(self.repo, "rev-parse", "HEAD").stdout, git(self.repo, "ls-files", "-s").stdout,
                  git(self.repo, "for-each-ref").stdout, git(self.repo, "status", "--porcelain").stdout)
        self.report()
        after = (git(self.repo, "rev-parse", "HEAD").stdout, git(self.repo, "ls-files", "-s").stdout,
                 git(self.repo, "for-each-ref").stdout, git(self.repo, "status", "--porcelain").stdout)
        self.assertEqual(before, after)

    def test_a_large_range_is_cut_at_the_byte_cap_and_says_so(self):
        self.commit("big.txt", "".join("line %d\n" % n for n in range(2000)) + "k = %s\n" % KEYS["sk-key"])
        with unittest.mock.patch.object(H, "MAX_SCAN", 4096):
            report = self.report()
        self.assertTrue(report["truncated"])
        self.assertEqual([], report["findings"])

    def test_findings_are_cut_at_the_count_cap_and_say_so(self):
        self.commit("many.txt", "".join("k%d = %s\n" % (n, KEYS["sk-key"]) for n in range(30)))
        with unittest.mock.patch.object(H, "MAX_FINDINGS", 5):
            report = self.report()
        self.assertEqual((5, True), (len(report["findings"]), report["truncated"]))

    def test_content_git_would_not_show_as_text_is_scanned_too(self):
        secret = KEYS["sk-key"]
        self.write(".gitattributes", "*.dat -diff\n*.bin binary\n")
        self.write("a.dat", "k = %s\n" % secret)
        self.write("b.bin", "k = %s\n" % secret)
        self.write("c.raw", b"\0\1\2 k = " + secret.encode() + b"\n")
        self.write("secret.pem", b"\0\1\2")
        git(self.repo, "add", "--", ".gitattributes", "a.dat", "b.bin", "c.raw", "secret.pem")
        git(self.repo, "commit", "-q", "-m", "hidden")
        found = sorted((f["path"], f["line"], f["rule"]) for f in self.report()["findings"])
        self.assertEqual([("a.dat", 1, "sk-key"), ("b.bin", 1, "sk-key"), ("c.raw", 1, "sk-key"),
                          ("secret.pem", None, "secret-file-name")], found)

    def test_a_secret_added_and_removed_inside_the_range_is_still_found(self):
        self.commit("k.txt", "k = %s\n" % KEYS["aws-access-key-id"], "add")
        self.commit("k.txt", "nothing\n", "remove")
        report = self.report()
        self.assertEqual(2, report["ahead"])
        self.assertEqual([{"path": "k.txt", "line": 1, "rule": "aws-access-key-id"}], report["findings"])

    def test_a_secret_in_a_merge_result_is_found_by_the_net_diff(self):
        git(self.repo, "switch", "-q", "-c", "side", self.first)
        self.commit("s.txt", "k = %s\n" % KEYS["sk-key"], "side")
        git(self.repo, "switch", "-q", "feature")
        git(self.repo, "merge", "-q", "--no-ff", "-m", "merge", "side")
        found = [(f["path"], f["rule"]) for f in self.report()["findings"]]
        self.assertEqual([("s.txt", "sk-key")], found)

    def test_a_changed_submodule_never_starts_a_program_its_own_configuration_names(self):
        marker = os.path.join(self.scratch, "ran")
        program = os.path.join(self.outside, "tool.sh")
        with open(program, "w") as handle:
            handle.write("#!/bin/sh\ntouch '%s'\nexit 0\n" % marker)
        os.chmod(program, 0o755)
        inner = os.path.join(self.repo, "sm")
        os.mkdir(inner)
        git(inner, "init", "-q")
        commits = []
        for number in (1, 2):
            with open(os.path.join(inner, "f.txt"), "w") as handle:
                handle.write("v%d\n" % number)
            git(inner, "add", "f.txt")
            git(inner, "commit", "-q", "-m", "c%d" % number)
            commits.append(git(inner, "rev-parse", "HEAD").stdout.strip())
        git(inner, "config", "diff.external", program)
        git(self.repo, "switch", "-q", self.main)
        git(self.repo, "update-index", "--add", "--cacheinfo", "160000,%s,sm" % commits[0])
        git(self.repo, "commit", "-q", "-m", "link")
        git(self.repo, "update-ref", "refs/remotes/origin/" + self.main, "HEAD")
        git(self.repo, "switch", "-q", "feature")
        git(self.repo, "reset", "-q", "--hard", self.main)
        git(self.repo, "update-index", "--cacheinfo", "160000,%s,sm" % commits[1])
        git(self.repo, "commit", "-q", "-m", "move the link")
        git(self.repo, "config", "diff.submodule", "diff")
        git(self.repo, "rm", "--cached", "-q", "sm")
        self.assertEqual("", git(self.repo, "ls-files", "-s", "sm").stdout)
        self.assertEqual(1, self.report()["ahead"])
        self.assertFalse(os.path.exists(marker))

    def test_a_tag_with_the_branchs_name_does_not_stop_the_check(self):
        git(self.repo, "tag", "feature")
        self.commit("a.txt", "x\n")
        self.assertEqual("feature", self.report()["branch"])

    def test_a_stuck_git_and_the_process_it_started_are_both_killed_at_the_deadline(self):
        pids = os.path.join(self.scratch, "pids")
        script = os.path.join(self.outside, "git")
        with open(script, "w") as handle:
            handle.write("#!/bin/sh\n/bin/sleep 300 &\necho $! > '%s'\nwait\n" % pids)
        os.chmod(script, 0o755)
        with unittest.mock.patch.dict(os.environ, {"PATH": self.outside, "HOME": self.scratch}, clear=True):
            with self.assertRaises(H.Refused):
                H.run_capped(["git", "diff", "--name-only", "-z", HEX + "..HEAD"], self.repo, 1000, timeout=1)
        with open(pids) as handle:
            grandchild = int(handle.read())
        for _ in range(50):
            try:
                os.kill(grandchild, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            os.kill(grandchild, 9)
            self.fail("the process the git started was left running")

    def test_a_cut_name_list_keeps_the_whole_names_it_read(self):
        for number in range(40):
            self.write("dir/file-%02d.txt" % number, "x\n")
        git(self.repo, "add", "--", "dir")
        git(self.repo, "commit", "-q", "-m", "many")
        with unittest.mock.patch.object(H, "MAX_SCAN", 200):
            report = self.report()
        self.assertTrue(report["truncated"])
        self.assertTrue(report["changed_paths"])
        self.assertTrue(all(len(path) == len("dir/file-00.txt") for path in report["changed_paths"]),
                        report["changed_paths"])

    def test_the_command_is_listed_in_the_usage(self):
        code, out, err = (lambda o, e: (H.main([], o, e, self.repo), o.getvalue(), e.getvalue()))(
            io.StringIO(), io.StringIO())
        self.assertEqual(1, code)
        self.assertIn("push-check", err)


if __name__ == "__main__":
    unittest.main()
