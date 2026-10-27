"""`safe-git describe push`, increment E (plan `2026-10-26-safe-git-describe-push`; `docs/specs/safe-git.md`,
"`describe push`", "The range" and "Facts of `describe push`"): the outgoing commits and their messages, the changed
paths, the credential-looking lines, whether the tracking ref's reflog looks written by git, and the diff.

Real repositories and real git. The facts are compared with what git itself says of the range `<base>..HEAD`; the
repository is byte for byte the same after every call, and no program that a configuration names is started. A value
over a cap is left out whole and named in `omitted`."""

import json
import os
import subprocess
import unittest

import support_git
from support_git import git, needs_git
import test_safegit_describe_push as base

H = base.H
RANGE = "a" * 40 + "..HEAD"
SECRET = "AKIA" + "ABCDEFGHIJKLMNOP"      # the shape of an AWS access key id, written in two pieces
SHAPE = ["--text", "--no-ext-diff", "--no-textconv", "--ignore-submodules=all", "--no-renames", "--no-color", "-U3",
         "--src-prefix=a/", "--dst-prefix=b/"]
LOG = ["log", "-z", "--reverse", "--topo-order", "--no-show-signature", "--encoding=UTF-8", "--format=%H%n%B", RANGE]
REFLOG = ["reflog", "show", "-z", "--no-show-signature", "--format=%gs", "refs/remotes/origin/main", "--"]
RAW = ["diff", "--raw", "-z", "--no-renames", "--no-ext-diff", "--no-textconv", "--ignore-submodules=none", RANGE]
PATCH = ["diff"] + SHAPE + [RANGE]


class Shapes(unittest.TestCase):
    def test_the_four_new_reads_are_accepted(self):
        for argv in (LOG, REFLOG, RAW, PATCH):
            self.assertTrue(H.git_shape_ok(["git"] + argv), argv)

    def test_the_log_of_the_messages_is_allowed_in_one_form_only(self):
        for index in range(len(LOG) - 1):
            self.assertFalse(H.git_shape_ok(["git"] + LOG[:index] + LOG[index + 1:]), LOG[index])
        for argv in (LOG[:-1], LOG[:-1] + ["HEAD..HEAD"], LOG + ["--"], LOG[:-1] + ["--all", RANGE],
                     LOG[:-1] + ["--no-merges", RANGE], LOG[:-1] + ["--output=x", RANGE],
                     LOG[:-1] + ["-n", "1", RANGE], [LOG[0], LOG[2], LOG[1]] + LOG[3:],
                     LOG[:-2] + ["--format=%H%n%B%x00", RANGE], LOG[:-2] + ["--format=%H%n%b", RANGE],
                     LOG[:-3] + ["--encoding=latin1", LOG[-2], RANGE]):
            self.assertFalse(H.git_shape_ok(["git"] + argv), argv)

    def test_the_reflog_read_is_one_form_of_a_tracking_ref(self):
        for ref in ("refs/remotes/origin/feature/x", "refs/remotes/a-b_c.d/main"):
            self.assertTrue(H.git_shape_ok(["git", "reflog", "show", "-z", "--no-show-signature", "--format=%gs", ref, "--"]), ref)
        for argv in (["reflog", "show", "-z", "--no-show-signature", "--format=%gs", "refs/heads/main", "--"],
                     ["reflog", "show", "-z", "--no-show-signature", "--format=%gs", "refs/tags/v1", "--"],
                     ["reflog", "show", "-z", "--no-show-signature", "--format=%gs", "HEAD", "--"],
                     ["reflog", "show", "-z", "--no-show-signature", "--format=%gs", "refs/remotes/o/../x", "--"],
                     ["reflog", "show", "-z", "--no-show-signature", "--format=%gs", "refs/remotes/origin/main"],
                     ["reflog", "show", "-z", "--no-show-signature", "--format=%gs", "--", "refs/remotes/origin/main"],
                     ["reflog", "show", "-z", "--no-show-signature", "--format=%gs", "refs/remotes/origin/main", "--", "x"],
                     ["reflog", "show", "-z", "--format=%gs", "refs/remotes/origin/main", "--"],
                     ["reflog", "show", "-z", "--format=%gs%x00", "refs/remotes/origin/main", "--"],
                     ["reflog", "show", "--no-show-signature", "--format=%gs", "refs/remotes/origin/main", "--"],
                     ["reflog", "show", "-z", "--no-show-signature", "--format=%gs", "-n", "1", "refs/remotes/origin/main", "--"],
                     ["reflog", "show", "-z", "--no-show-signature", "--format=%gs", "--all", "--"],
                     ["reflog", "expire", "--all"], ["reflog", "delete", "refs/remotes/origin/main"],
                     ["reflog", "exists", "refs/remotes/origin/main"], ["reflog"],
                     ["reflog", "show", "-z", "--no-show-signature", "--format=%gs", "refs/remotes/origin/main", "refs/remotes/origin/x",
                      "--"]):
            self.assertFalse(H.git_shape_ok(["git"] + argv), argv)

    def test_the_raw_diff_and_the_text_diff_need_no_filter_and_no_external_program(self):
        for argv in (RAW[:3] + RAW[5:], RAW[:4] + RAW[5:], RAW[:-1] + ["--output=x", RAW[-1]],
                     RAW[:-2] + ["--ignore-submodules=dirty", RAW[-1]], RAW[:-1] + ["--ext-diff", RAW[-1]],
                     PATCH[:2] + PATCH[3:], PATCH[:3] + PATCH[4:], PATCH[:-1] + ["--output=x", PATCH[-1]],
                     PATCH[:-1] + ["-U3", PATCH[-1]], PATCH[:-1] + ["--textconv", PATCH[-1]],
                     PATCH[:-1] + ["--src-prefix=/etc/", PATCH[-1]]):
            self.assertFalse(H.git_shape_ok(["git"] + argv), argv)

    def test_leaving_submodules_in_is_allowed_only_for_a_raw_diff_of_a_range(self):
        none = "--ignore-submodules=none"
        for argv in (["diff", "--name-only", none, "--", "x"], ["diff", "--name-only", none],
                     ["diff", "--name-only", "-z", none, RANGE], ["diff", "--no-ext-diff", "--no-textconv", none, RANGE],
                     ["diff", "--no-ext-diff", "--no-textconv", none, "--", "x"]):
            self.assertFalse(H.git_shape_ok(["git"] + argv), argv)
        self.assertTrue(H.git_shape_ok(["git"] + RAW))

    def test_the_other_shapes_of_a_reflog_and_a_log_stay_refused(self):
        self.assertFalse(H.git_shape_ok(["git", "log", "-z", "--format=%H%n%B", RANGE]))
        self.assertFalse(H.git_shape_ok(["git", "log", "-g", "--format=%gs", "refs/remotes/origin/main"]))


@needs_git
class Outgoing(base.Push):
    def setUp(self):
        super().setUp()
        self.git_env = {"PATH": base.STANDARD, "HOME": self.scratch, "GIT_CONFIG_NOSYSTEM": "1"}

    def facts(self, *args):
        return self.describe(*args)["facts"]

    def outcome(self, *args):
        """The object `describe push <args>` prints, as it is whether or not a fact was left out, after checking that
        the repository is unchanged."""
        before = base.snapshot(self.repo)
        code, text, err = self.call(*args)
        self.assertEqual((0, ""), (code, err), text)
        built = json.loads(text)
        self.assertEqual(before, base.snapshot(self.repo))
        return built

    def revs(self):
        return git(self.repo, "rev-list", "--reverse", "--topo-order", self.first + "..HEAD").stdout.split()

    def message_of(self, commit):
        return git(self.repo, "log", "-1", "--format=%B", commit).stdout[:-1]

    def real_diff(self):
        return git(self.repo, "diff", *SHAPE, self.first + "..HEAD").stdout

    def verbatim(self, text):
        """A commit with no change whose message is exactly `text`."""
        path = os.path.join(self.scratch, "message")
        with open(path, "wb") as handle:
            handle.write(text)
        git(self.repo, "commit", "-q", "--allow-empty", "--cleanup=verbatim", "-F", path)
        return git(self.repo, "rev-parse", "HEAD").stdout.strip()

    def raw_commit(self, message):
        """A commit on the branch whose message is exactly the bytes `message`. `git commit` and `git commit-tree`
        convert a message that is not UTF-8, so the object is written as it is."""
        head = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        tree = git(self.repo, "rev-parse", "HEAD^{tree}").stdout.strip()
        body = ("tree %s\nparent %s\nauthor t <t@example.invalid> 1 +0000\ncommitter t <t@example.invalid> 1 +0000\n\n"
                % (tree, head)).encode() + message
        made = subprocess.run([support_git.REAL_GIT, "hash-object", "-t", "commit", "-w", "--stdin"], cwd=self.repo,
                              env=dict(support_git._CLEAN, HOME=self.scratch), input=body, capture_output=True)
        self.assertEqual(0, made.returncode, made.stderr)
        commit = made.stdout.decode().strip()
        git(self.repo, "update-ref", "refs/heads/feature", commit)
        return commit

    def commits(self, count):
        """`count` more commits on the branch, made without touching the work tree."""
        tree = git(self.repo, "rev-parse", "HEAD^{tree}").stdout.strip()
        parent = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        for number in range(count):
            parent = git(self.repo, "commit-tree", tree, "-p", parent, "-m", "c%d" % number).stdout.strip()
        git(self.repo, "update-ref", "refs/heads/feature", parent)


class Commits(Outgoing):
    def test_the_hashes_and_the_messages_are_those_of_git_log_oldest_first(self):
        one = self.commit("b.txt", "two\n", "second")
        two = self.commit("c.txt", "three\n", "third\n\nbody line\n\nPlan: x#A")
        facts = self.facts()
        self.assertEqual([one, two], facts["commit_hashes"])
        self.assertEqual([self.message_of(one), self.message_of(two)], facts["commit_messages"])
        self.assertEqual(self.revs(), facts["commit_hashes"])
        self.assertEqual(2, facts["ahead"])

    def test_a_merge_commit_is_one_of_the_commits_and_counts_in_ahead(self):
        git(self.repo, "switch", "-q", "-c", "side")
        side = self.commit("s.txt", "s\n", "side work")
        git(self.repo, "switch", "-q", "feature")
        own = self.commit("f.txt", "f\n", "feature work")
        git(self.repo, "merge", "-q", "--no-ff", "-m", "merge the side", "side")
        merge = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        facts = self.facts()
        self.assertEqual(3, facts["ahead"])
        self.assertEqual({side, own, merge}, set(facts["commit_hashes"]))
        self.assertEqual(merge, facts["commit_hashes"][-1])
        self.assertEqual(self.revs(), facts["commit_hashes"])
        self.assertEqual("merge the side\n", facts["commit_messages"][-1])
        self.assertEqual(["f.txt", "s.txt"], facts["changed_paths"])

    def test_a_range_with_no_commit_has_empty_lists_and_an_empty_diff(self):
        facts = self.facts()
        self.assertEqual(0, facts["ahead"])
        for name in ("commit_hashes", "commit_messages", "changed_paths", "binary_paths", "submodule_paths",
                     "findings"):
            self.assertEqual([], facts[name], name)
        self.assertEqual("", facts["diff"])

    def test_a_branch_behind_its_tracking_ref_sends_nothing_and_the_diff_is_empty(self):
        ahead = self.commit("x.txt", "x\n")
        git(self.repo, "update-ref", "refs/remotes/origin/" + self.main, ahead)
        git(self.repo, "switch", "-q", self.main)
        facts = self.facts()
        self.assertEqual((ahead, 0), (facts["base"], facts["ahead"]))
        self.assertEqual(([], [], ""), (facts["commit_hashes"], facts["changed_paths"], facts["diff"]))

    def test_control_characters_in_a_message_are_kept_and_printed_escaped(self):
        commit = self.verbatim(b"ctl \x01\x1b[0m\ttab \x7f end\n\n\n  indented\n")
        built = self.outcome()
        self.assertEqual([self.message_of(commit)], built["facts"]["commit_messages"])
        self.assertIn("\\u0001", json.dumps(built))

    def test_a_message_of_exactly_the_element_cap_is_kept_and_one_byte_more_is_left_out(self):
        self.verbatim(b"x" * 1023 + b"\n")
        facts = self.facts()
        self.assertEqual(1024, len(facts["commit_messages"][0].encode()))
        self.verbatim(b"y" * 1024 + b"\n")
        built = self.outcome()
        self.assertEqual(["commit_messages"], built["facts"]["omitted"])
        self.assertTrue(built["truncated"])
        self.assertTrue(built["ok"])
        self.assertNotIn("commit_messages", built["facts"])
        self.assertEqual(2, len(built["facts"]["commit_hashes"]))

    def test_a_message_that_is_not_utf8_is_printed_as_text_a_strict_reader_accepts(self):
        commit = self.raw_commit(b"caf\xe9 au lait\n")
        code, text, err = self.call()
        self.assertEqual((0, ""), (code, err))
        built = json.loads(text, parse_constant=self.fail)
        self.assertEqual("caf\\udce9 au lait\n", built["facts"]["commit_messages"][0])
        self.assertEqual([commit], built["facts"]["commit_hashes"])
        text.encode("ascii")

    def test_two_hundred_commits_are_listed_and_two_hundred_and_one_are_left_out_whole(self):
        self.commits(200)
        facts = self.facts()
        self.assertEqual((200, 200, 200), (facts["ahead"], len(facts["commit_hashes"]),
                                           len(facts["commit_messages"])))
        self.assertEqual("c0\n", facts["commit_messages"][0])
        self.commits(1)
        built = self.outcome()
        self.assertEqual(201, built["facts"]["ahead"])
        self.assertEqual(["commit_hashes", "commit_messages"], built["facts"]["omitted"])
        self.assertTrue(built["truncated"])
        self.assertTrue(built["ok"])
        self.assertEqual([], built["facts"]["changed_paths"])


class Whole(Outgoing):
    def test_what_does_not_fit_the_object_is_left_out_from_the_last_fact_and_the_object_stays_under_the_cap(self):
        self.write("big.txt", ("y" * 79 + "\n") * 700)
        git(self.repo, "add", "big.txt")
        git(self.repo, "commit", "-q", "-m", "big")
        tree = git(self.repo, "rev-parse", "HEAD^{tree}").stdout.strip()
        parent = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        for number in range(150):
            parent = git(self.repo, "commit-tree", tree, "-p", parent, "-m", "m%03d%s" % (number, "x" * 1000)).stdout.strip()
        git(self.repo, "update-ref", "refs/heads/feature", parent)
        code, text, err = self.call()
        self.assertEqual((0, ""), (code, err))
        self.assertLessEqual(len(text.encode()), H.MAX_OBJECT)
        built = json.loads(text)
        self.assertTrue(built["ok"])
        self.assertTrue(built["truncated"])
        self.assertEqual(["diff"], built["facts"]["omitted"])
        self.assertEqual(151, len(built["facts"]["commit_messages"]))
        self.assertEqual(151, len(built["facts"]["commit_hashes"]))
        self.assertEqual(["big.txt"], built["facts"]["changed_paths"])


class Paths(Outgoing):
    def test_the_changed_paths_are_those_of_git_with_the_deleted_ones(self):
        self.commit("b.txt", "two\n")
        self.write("sp ace.txt", "s\n")
        self.write("dir/café.txt", "c\n")
        self.write("a.txt", "one\nmore\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "several")
        git(self.repo, "rm", "-q", "b.txt")
        git(self.repo, "commit", "-q", "-m", "gone")
        facts = self.facts()
        listing = git(self.repo, "diff", "--name-only", "-z", "--no-renames", self.first + "..HEAD").stdout
        self.assertEqual([item for item in listing.split("\0") if item], facts["changed_paths"])
        self.assertEqual(["a.txt", "dir/café.txt", "sp ace.txt"], facts["changed_paths"])

    def test_a_path_the_range_deletes_is_listed(self):
        git(self.repo, "rm", "-q", "a.txt")
        git(self.repo, "commit", "-q", "-m", "delete the old file")
        self.assertEqual(["a.txt"], self.facts()["changed_paths"])

    def test_two_hundred_paths_are_listed_and_two_hundred_and_one_are_left_out_whole(self):
        for number in range(200):
            self.write("many/f%03d.txt" % number, "x\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "many")
        self.assertEqual(200, len(self.facts()["changed_paths"]))
        self.write("many/extra.txt", "x\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "one more")
        built = self.outcome()
        self.assertEqual(["changed_paths"], built["facts"]["omitted"])
        self.assertTrue(built["truncated"])
        self.assertTrue(built["ok"])

    def test_a_binary_path_and_a_path_that_is_not_utf8_are_listed_and_their_hunks_are_left_out(self):
        self.write("bin", b"a\0b\n")
        self.write("lat", b"caf\xe9\n")
        self.write("t.txt", "text\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "mixed")
        facts = self.facts()
        self.assertEqual(["bin", "lat", "t.txt"], facts["changed_paths"])
        self.assertEqual(["bin", "lat"], facts["binary_paths"])
        self.assertIn("diff --git a/t.txt b/t.txt\n", facts["diff"])
        self.assertIn("+text\n", facts["diff"])
        for name in ("bin", "lat"):
            self.assertNotIn(name, facts["diff"])
        self.assertNotIn("\0", facts["diff"])

    def test_a_path_git_quotes_in_the_patch_is_read_back_whole(self):
        names = ['we"ird.txt', "tab\there.txt", "new\nline.txt", "back\\slash.txt", "caf\u00e9 \u4e2d.txt", "sp ace b/x.txt"]
        for name in names:
            self.write(name, "text of %d\n" % len(name))
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "odd names")
        facts = self.facts()
        self.assertEqual(sorted(names), sorted(facts["changed_paths"]))
        self.assertEqual([], facts["binary_paths"])
        self.assertEqual(self.real_diff(), facts["diff"])
        self.assertEqual(len(names), facts["diff"].count("\ndiff --git ") + 1)

    def test_an_attribute_that_marks_a_path_binary_does_not_hide_its_hunks(self):
        self.write(".gitattributes", "*.dat -diff\n*.bin binary\n")
        self.write("x.dat", "text\n")
        self.write("y.bin", "more text\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "marked")
        facts = self.facts()
        self.assertEqual([], facts["binary_paths"])
        self.assertIn("+text\n", facts["diff"])
        self.assertIn("+more text\n", facts["diff"])
        self.assertEqual(self.real_diff(), facts["diff"])

    def test_a_deleted_binary_file_and_a_text_file_that_gains_a_nul_line_are_binary(self):
        self.write("bin", b"a\0b\n")
        self.write("mix.txt", "one\n" * 10)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "add")
        git(self.repo, "update-ref", "refs/remotes/origin/feature", git(self.repo, "rev-parse", "HEAD").stdout.strip())
        git(self.repo, "rm", "-q", "bin")
        self.write("mix.txt", "one\n" * 5 + "\0\n" + "one\n" * 4)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "remove and change")
        facts = self.facts()
        self.assertEqual(["bin", "mix.txt"], facts["binary_paths"])
        self.assertEqual("", facts["diff"])

    def test_a_changed_gitlink_is_listed_even_where_the_configuration_ignores_submodules(self):
        link = "160000,%s,mod"
        git(self.repo, "update-index", "--add", "--cacheinfo", link % ("1" * 40))
        self.write(".gitmodules", '[submodule "mod"]\n\tpath = mod\n\turl = ../sub\n\tignore = all\n')
        git(self.repo, "add", ".gitmodules")
        git(self.repo, "commit", "-q", "-m", "add the link")
        self.config("diff.ignoreSubmodules", "all")
        git(self.repo, "update-index", "--cacheinfo", link % ("2" * 40))
        git(self.repo, "commit", "-q", "-m", "move the link")
        # A repository with a gitlink in its index is refused as one that selects a program; the range is read
        # where the index does not hold the link (a staged removal), which is how a link reaches this fact.
        refused = self.refused("repo_selects_program")
        self.assertIn("submodule:mod", refused["errors"][0]["message"])
        git(self.repo, "rm", "-q", "--cached", "mod")
        facts = self.facts()
        self.assertEqual(["mod"], facts["submodule_paths"])
        self.assertEqual([".gitmodules", "mod"], facts["changed_paths"])
        self.assertEqual([], facts["binary_paths"])
        self.assertIn("diff --git a/.gitmodules b/.gitmodules\n", facts["diff"])
        self.assertNotIn("a/mod", facts["diff"])
        self.assertNotIn("Subproject", facts["diff"])

    def test_a_link_added_and_removed_inside_the_range_is_not_a_changed_path(self):
        git(self.repo, "update-index", "--add", "--cacheinfo", "160000,%s,mod" % ("1" * 40))
        git(self.repo, "commit", "-q", "-m", "add the link")
        git(self.repo, "rm", "-q", "--cached", "mod")
        git(self.repo, "commit", "-q", "-m", "remove the link")
        facts = self.facts()
        self.assertEqual((2, [], []), (facts["ahead"], facts["changed_paths"], facts["submodule_paths"]))


class Findings(Outgoing):
    def test_a_secret_added_and_removed_inside_the_range_is_found_by_rule_line_and_path(self):
        self.commit("sp ace/keys.txt", "key = %s\n" % SECRET)
        self.commit("sp ace/keys.txt", "key = removed\n")
        code, text, err = self.call()
        self.assertEqual((0, ""), (code, err))
        built = json.loads(text)
        self.assertEqual(["aws-access-key-id 1 sp ace/keys.txt"], built["facts"]["findings"])
        self.assertNotIn(SECRET, text)

    def test_a_secret_still_in_the_net_change_is_found_once(self):
        self.commit("keys.txt", "one\n%s\n" % SECRET)
        facts = self.facts()
        self.assertEqual(["aws-access-key-id 2 keys.txt"], facts["findings"])
        self.assertIn(SECRET, facts["diff"])      # the diff is the evidence the engine scans; findings carry no text

    def test_no_finding_where_nothing_matches(self):
        self.commit("keys.txt", "nothing here\n")
        self.assertEqual([], self.facts()["findings"])

    def test_the_findings_are_left_out_whole_past_one_hundred(self):
        self.commit("keys.txt", "%s\n" % SECRET * 100)
        self.assertEqual(100, len(self.facts()["findings"]))
        self.commit("more.txt", "%s\n" % SECRET)
        built = self.outcome()
        self.assertEqual(["findings"], built["facts"]["omitted"])
        self.assertTrue(built["truncated"])
        self.assertTrue(built["ok"])


class Diff(Outgoing):
    def test_the_diff_is_what_git_says_of_the_text_paths(self):
        self.commit("b.txt", "two\nthree")
        self.write("a.txt", "one\n" + "more\n" * 3)
        self.write("dir/c.txt", "c\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "more")
        git(self.repo, "rm", "-q", "b.txt")
        git(self.repo, "commit", "-q", "-m", "gone")
        facts = self.facts()
        self.assertEqual(self.real_diff(), facts["diff"])

    def test_a_missing_final_newline_and_a_mode_change_are_in_the_diff(self):
        self.commit("b.txt", "two\nthree")
        os.chmod(os.path.join(self.repo, "a.txt"), 0o755)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "mode")
        facts = self.facts()
        self.assertEqual(self.real_diff(), facts["diff"])
        self.assertIn("old mode 100644\nnew mode 100755\n", facts["diff"])
        self.assertIn("\\ No newline at end of file\n", facts["diff"])

    def test_a_rename_is_a_deletion_and_an_addition(self):
        git(self.repo, "mv", "a.txt", "c.txt")
        git(self.repo, "commit", "-q", "-m", "rename")
        facts = self.facts()
        self.assertEqual(["a.txt", "c.txt"], facts["changed_paths"])
        self.assertEqual(self.real_diff(), facts["diff"])
        self.assertNotIn("rename from", facts["diff"])

    def big(self, size):
        """A commit whose diff against the first one is exactly `size` bytes, a new file of long lines."""
        full, path = "y" * 79 + "\n", os.path.join(self.repo, "big.txt")
        def make(last):
            with open(path, "w") as handle:
                handle.write(full * 1100 + "z" * last + "\n")
            git(self.repo, "add", "big.txt")
            return len(git(self.repo, "diff", "--cached", *SHAPE).stdout.encode())
        last = 1 + size - make(1)
        self.assertEqual(size, make(last))
        git(self.repo, "commit", "-q", "-m", "big")
        self.assertEqual(size, len(self.real_diff().encode()))

    def test_a_diff_of_exactly_the_cap_is_kept(self):
        self.big(H.MAX_DIFF)
        built = self.outcome()
        self.assertEqual(H.MAX_DIFF, len(built["facts"]["diff"].encode()))
        self.assertEqual(self.real_diff(), built["facts"]["diff"])
        self.assertEqual(([], False), (built["facts"]["omitted"], built["truncated"]))

    def test_a_diff_one_byte_over_the_cap_is_left_out_whole(self):
        self.big(H.MAX_DIFF + 1)
        built = self.outcome()
        self.assertEqual(["diff"], built["facts"]["omitted"])
        self.assertTrue(built["truncated"])
        self.assertTrue(built["ok"])
        self.assertNotIn("diff", built["facts"])
        self.assertEqual(["big.txt"], built["facts"]["changed_paths"])

    def test_a_filter_a_text_conversion_and_an_external_diff_of_the_owners_configuration_are_never_started(self):
        marker = os.path.join(self.scratch, "ran")
        script = self.write("../tool.sh", "#!/bin/sh\ntouch '%s'\n" % marker, mode=0o755)
        self.global_config('[diff "bad"]\n\ttextconv = %s\n\tcommand = %s\n[diff]\n\texternal = %s\n'
                           '[filter "bad"]\n\tclean = %s\n\tsmudge = %s\n' % ((script,) * 5))
        self.write(".gitattributes", "* diff=bad filter=bad\n")
        self.write("a.txt", "one\ntwo\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "attributes")
        built = self.describe()
        self.assertTrue(built["ok"], built["errors"])
        self.assertIn("+two\n", built["facts"]["diff"])
        self.assertFalse(os.path.exists(marker))
        # The control: git itself, run with that configuration, does start the program for the same range.
        env = dict(self.git_env, GIT_CONFIG_GLOBAL=os.path.join(self.scratch, ".gitconfig"))
        subprocess.run([support_git.REAL_GIT, "diff", self.first + "..HEAD"], cwd=self.repo, env=env,
                       capture_output=True, text=True, timeout=60)
        self.assertTrue(os.path.exists(marker), "the control did not start the program")


class Reflog(Outgoing):
    def tracking(self, *messages, ref="feature"):
        """Update `refs/remotes/origin/<ref>` once for each message, oldest first, so that it ends at the first commit.
        Each update changes the value, so each writes an entry."""
        tip = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        for index, message in enumerate(messages):
            value = self.first if (len(messages) - 1 - index) % 2 == 0 else tip
            git(self.repo, "update-ref", "-m", message, "refs/remotes/origin/" + ref, value)

    def looks(self):
        return self.facts()["tracking_ref_reflog_looks_git_written"]

    def test_a_ref_a_fetch_wrote_looks_git_written(self):
        self.commit("b.txt", "two\n")
        self.tracking("fetch origin: storing head", "fetch origin: fast-forward")
        self.assertIs(True, self.looks())

    def test_a_ref_a_push_wrote_looks_git_written(self):
        self.commit("b.txt", "two\n")
        self.tracking("update by push")
        self.assertIs(True, self.looks())

    def test_a_ref_written_by_hand_does_not(self):
        self.commit("b.txt", "two\n")
        self.tracking("manual edit")
        self.assertIs(False, self.looks())

    def test_one_entry_by_hand_among_fetches_is_enough(self):
        self.commit("b.txt", "two\n")
        self.tracking("fetch origin: storing head", "manual edit", "fetch origin: fast-forward")
        self.assertIs(False, self.looks())

    def test_a_forged_reflog_fools_the_heuristic_and_that_is_the_recorded_limit(self):
        self.commit("b.txt", "two\n")
        self.tracking("fetch origin: forged by hand with update-ref -m")
        self.assertIs(True, self.looks())

    def test_a_ref_with_no_message_or_no_reflog_gives_null(self):
        self.commit("b.txt", "two\n")
        self.assertIsNone(self.looks())      # the main tracking ref was written with no message
        os.remove(os.path.join(self.repo, ".git", "logs", "refs", "remotes", "origin", self.main))
        self.assertIsNone(self.looks())

    def test_it_is_the_reflog_of_the_ref_that_gave_the_base(self):
        self.commit("b.txt", "two\n")
        os.remove(os.path.join(self.repo, ".git", "logs", "refs", "remotes", "origin", self.main))
        self.tracking("fetch origin: storing head", "fetch origin: fast-forward", ref=self.main)
        self.assertIs(True, self.looks())
        self.tracking("manual edit")
        self.assertIs(False, self.looks())

    def test_a_deletion_has_no_tracking_ref(self):
        facts = self.facts("--delete", "origin", "refs/heads/other")
        self.assertIsNone(facts["tracking_ref_reflog_looks_git_written"])
        self.assertEqual(([], [], [], [], [], ""), (facts["commit_hashes"], facts["commit_messages"],
                                                    facts["changed_paths"], facts["findings"],
                                                    facts["binary_paths"], facts["diff"]))
        self.assertEqual((None, 0), (facts["base"], facts["ahead"]))


class Refusals(Outgoing):
    BLANK = ("commit_hashes", "commit_messages", "changed_paths", "binary_paths", "submodule_paths", "findings")

    def test_a_refusal_gives_no_outgoing_fact(self):
        self.commit("b.txt", "two\n")
        for code, args in (("usage", ("--all",)), ("remote_unconfigured", ("nowhere",))):
            built = self.refused(code, *args)
            facts = built["facts"]
            self.assertEqual(([], [], [], [], [], []), tuple(facts[name] for name in self.BLANK), code)
            self.assertEqual((None, None), (facts["diff"], facts["tracking_ref_reflog_looks_git_written"]), code)

    def test_a_branch_with_no_base_gives_no_outgoing_fact(self):
        self.commit("b.txt", "two\n")
        self.remote("nowhere", "https://example.invalid/x.git")
        facts = self.refused("base_unresolved", "nowhere")["facts"]
        self.assertEqual(([], None), (facts["commit_hashes"], facts["diff"]))


class Reads(Outgoing):
    def test_every_read_is_a_shape_the_helper_allows_and_none_reaches_the_remote(self):
        self.commit("b.txt", "two\n")
        directory = self.recording_git()
        code, text, err = self.call(path=directory + os.pathsep + base.STANDARD)
        self.assertEqual((0, ""), (code, err))
        self.assertTrue(json.loads(text)["ok"])
        commands = {arguments[0] for arguments, _ in self.runs()}
        self.assertTrue({"reflog", "log", "diff", "rev-list", "config"} <= commands, commands)
        self.assertFalse(commands & {"push", "fetch", "ls-remote", "pull", "clone", "checkout", "switch", "merge",
                                     "rebase", "tag", "branch", "commit", "add", "reset", "gc", "prune"}, commands)
        self.assertTrue(all(H.git_shape_ok(["git"] + arguments) for arguments, _ in self.runs()))


if __name__ == "__main__":
    unittest.main()
