"""`safe-git describe push`, increment D (plan `2026-10-26-safe-git-describe-push`; `docs/specs/safe-git.md`,
"`describe push`", "The grammar"): which remote refs the push asks to update or delete, from the refspecs of the
command and from `remote.<name>.push` and `push.default`.

The remote is a bare repository in a temporary directory, and the facts are compared with what a real `git push
--porcelain` of the same arguments to it updated or deleted. Nothing is pushed anywhere else. A case that cannot be
resolved from local data gives empty lists and a code, never a guess."""

import os
import unittest

import support_git
from support_git import git, needs_git
import test_safegit_describe_push as base

H = base.H


@needs_git
class Target(base.Push):
    def setUp(self):
        super().setUp()
        self.bare = self.bare_remote("remote.git", "local")

    def bare_remote(self, directory, name):
        """A bare repository as a remote that already holds the main branch, with its tracking refs."""
        path = os.path.join(self.scratch, directory)
        git(self.scratch, "init", "-q", "--bare", path)
        self.remote(name, path)
        git(self.repo, "push", "-q", name, self.main)
        git(self.repo, "symbolic-ref", "refs/remotes/%s/HEAD" % name, "refs/remotes/%s/%s" % (name, self.main))
        return path

    def add(self, key, value):
        git(self.repo, "config", "--add", key, value)

    def unset(self, key):
        git(self.repo, "config", "--unset-all", key)

    def real(self, *args):
        """What a real `git push --porcelain` of `args` updated and deleted, and what it forced:
        ``(updates, deletes, forced)`` as ``<source>:<destination>``, destinations, and destinations."""
        done = git(self.repo, "push", "--porcelain", *args, check=False)
        self.assertEqual(0, done.returncode, done.stderr)
        updates, deletes, forced = [], [], []
        for line in done.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) == 3 and parts[0] in (" ", "+", "-", "*", "=", "!"):
                source, _, destination = parts[1].partition(":")
                if source:
                    updates.append("%s:%s" % (source, destination))
                else:
                    deletes.append(destination)
                if parts[0] == "+":
                    forced.append(destination)
        return updates, deletes, forced

    def agree(self, *args, **more):
        """The facts of `args`, after checking that they equal what a real push of them does."""
        built = self.describe(*args, **more)
        self.assertEqual([], built["errors"], built)
        facts = built["facts"]
        updates, deletes, forced = self.real(*args)
        self.assertEqual(sorted(updates), sorted(facts["push_updates"]))
        self.assertEqual(sorted(deletes), sorted(facts["push_deletes"]))
        self.assertLessEqual(set(forced), set(facts["push_forced"]))
        return facts

    def unresolved(self, *args, code="target_unresolved"):
        """A refusal with `code` that leaves the three lists empty."""
        built = self.refused(code, *args)
        for name in ("push_updates", "push_deletes", "push_forced"):
            self.assertEqual([], built["facts"][name], name)
        return built

    def create(self, name, ref="refs/heads/"):
        """A ref on the remote, made by a real push."""
        git(self.repo, "push", "-q", "local", "HEAD:" + ref + name)


class Refspecs(Target):
    def test_the_forms_of_an_update_agree_with_a_real_push(self):
        self.commit("b.txt", "two\n")
        for args in (("local", "HEAD"), ("local", "feature"), ("local", "refs/heads/feature"),
                     ("local", "HEAD:other"), ("local", "feature:another"),
                     ("local", "refs/heads/feature:refs/heads/third"), ("local", "HEAD:refs/tags/v1"),
                     ("local", "HEAD:deep/er/branch"), ("local", "feature:refs/heads/fourth")):
            with self.subTest(args=args):
                facts = self.agree(*args)
                self.assertEqual(([], []), (facts["push_deletes"], facts["push_forced"]))
                self.assertEqual(1, len(facts["push_updates"]))

    def test_a_bare_head_goes_to_the_current_branch(self):
        self.commit("b.txt", "two\n")
        self.assertEqual(["HEAD:refs/heads/feature"], self.agree("local", "HEAD")["push_updates"])

    def test_the_source_is_shown_as_git_shows_it(self):
        updates = [self.describe("local", spelled)["facts"]["push_updates"]
                   for spelled in ("HEAD:x", "feature:x", "refs/heads/feature:x")]
        self.assertEqual([["HEAD:refs/heads/x"], ["refs/heads/feature:refs/heads/x"],
                          ["refs/heads/feature:refs/heads/x"]], updates)

    def test_a_destination_under_tags_is_kept(self):
        facts = self.agree("local", "HEAD:refs/tags/v1")
        self.assertEqual(["HEAD:refs/tags/v1"], facts["push_updates"])

    def test_head_as_a_destination_is_usage(self):
        self.refused("usage", "local", "HEAD:HEAD")      # git would make a branch named HEAD

    def test_a_source_other_than_the_current_branch_is_usage(self):
        self.refused("usage", "local", self.main + ":x")
        self.refused("usage", "local", "v1:x")

    def test_a_force_flag_or_a_plus_forces_the_destination(self):
        self.commit("b.txt", "two\n")
        for args, forced in ((("-f", "local", "feature:" + self.main), ["refs/heads/" + self.main]),
                             (("--force", "local", "feature"), ["refs/heads/feature"]),
                             (("--force-with-lease", "local", "feature:x"), ["refs/heads/x"]),
                             (("local", "+feature:y"), ["refs/heads/y"]), (("local", "feature:z"), [])):
            with self.subTest(args=args):
                self.assertEqual(forced, self.agree(*args)["push_forced"])

    def test_a_push_that_a_real_push_forces_is_listed(self):
        self.commit("b.txt", "two\n")
        git(self.repo, "push", "-q", "local", "feature:refs/heads/diverged")
        git(self.repo, "commit", "-q", "--amend", "-m", "rewritten")
        facts = self.describe("local", "+feature:diverged")["facts"]
        updates, deletes, forced = self.real("local", "+feature:diverged")
        self.assertEqual(["refs/heads/diverged"], forced)       # the real push did force it
        self.assertEqual(forced, facts["push_forced"])
        self.assertEqual(updates, facts["push_updates"])

    def test_two_sources_and_one_destination_is_not_a_single_update(self):
        self.refused("usage", "local", "feature:x", "feature:x")

    def test_a_name_that_is_a_branch_and_a_tag_is_unresolved(self):
        git(self.repo, "tag", "feature")
        self.unresolved("local", "feature")
        self.unresolved("local", "feature:x")
        self.assertEqual(["refs/heads/feature:refs/heads/feature"],
                         self.describe("local", "refs/heads/feature")["facts"]["push_updates"])
        self.assertEqual(["HEAD:refs/heads/feature"], self.describe("local", "HEAD")["facts"]["push_updates"])
        self.assertNotEqual(0, git(self.repo, "push", "--porcelain", "local", "feature", check=False).returncode)

    def test_a_destination_the_remote_could_read_as_another_ref_is_unresolved(self):
        for destination in ("heads/zz", "tags/zz", "remotes/origin/zz"):
            with self.subTest(destination=destination):
                self.unresolved("local", "HEAD:" + destination)

    def test_a_long_destination_still_gives_an_object(self):
        name = "a" * 195      # its tracking ref is longer than the helper reads
        built = self.describe("local", "HEAD:" + name)
        self.assertEqual([], built["errors"])
        self.assertEqual(["HEAD:refs/heads/" + name], built["facts"]["push_updates"])


class Deletions(Target):
    def test_a_deletion_by_a_full_ref_agrees_with_a_real_push(self):
        for spelled in (("--delete", "local", "refs/heads/gone"), ("local", ":refs/heads/gone"),
                        ("-d", "local", "refs/heads/gone")):
            with self.subTest(args=spelled):
                self.create("gone")
                facts = self.agree(*spelled)
                self.assertEqual((["refs/heads/gone"], [], []), (facts["push_deletes"], facts["push_updates"],
                                                                 facts["push_forced"]))
                self.assertEqual((None, 0), (facts["base"], facts["ahead"]))

    def test_a_tag_can_be_deleted(self):
        self.create("v9", "refs/tags/")
        self.assertEqual(["refs/tags/v9"], self.agree("--delete", "local", "refs/tags/v9")["push_deletes"])

    def test_two_deletions_are_listed(self):
        self.create("one")
        self.create("two")
        facts = self.agree("--delete", "local", "refs/heads/one", "refs/heads/two")
        self.assertEqual(["refs/heads/one", "refs/heads/two"], facts["push_deletes"])

    def test_a_bare_name_could_be_a_branch_or_a_tag_there(self):
        self.create("gone")
        self.unresolved("--delete", "local", "gone")
        self.unresolved("local", ":gone")

    def test_an_unresolved_name_is_not_quoted(self):
        token = "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0" * 2
        built = self.unresolved("--delete", "local", token)
        self.assertNotIn(token, built["errors"][0]["message"])

    def test_a_force_flag_forces_a_deletion_too(self):
        self.create("gone")
        self.assertEqual(["refs/heads/gone"], self.describe("-f", "--delete", "local",
                                                            "refs/heads/gone")["facts"]["push_forced"])


class WithoutARefspec(Target):
    """`push.default`, as Git itself behaves for each value (probed with a real push to a bare remote)."""

    def setUp(self):
        super().setUp()
        self.unset("push.default")
        self.commit("b.txt", "two\n")

    def upstream(self, remote="local", merge=None):
        self.config("branch.feature.remote", remote)
        self.config("branch.feature.merge", merge or "refs/heads/feature")

    def real_fails(self, *args):
        self.assertNotEqual(0, git(self.repo, "push", "--porcelain", *args, check=False).returncode)

    def test_current_pushes_the_branch_to_its_own_name(self):
        self.config("push.default", "current")
        self.assertEqual(["refs/heads/feature:refs/heads/feature"], self.agree("local")["push_updates"])

    def test_current_ignores_the_upstream(self):
        self.config("push.default", "current")
        self.upstream(merge="refs/heads/" + self.main)
        self.assertEqual(["refs/heads/feature:refs/heads/feature"], self.agree("local")["push_updates"])

    def test_the_unset_default_is_simple(self):
        self.upstream()
        self.assertEqual(["refs/heads/feature:refs/heads/feature"], self.agree("local")["push_updates"])

    def test_simple_with_an_upstream_of_another_name_is_unresolved(self):
        self.upstream(merge="refs/heads/" + self.main)
        self.unresolved("local")
        self.real_fails("local")

    def test_simple_without_an_upstream_is_unresolved(self):
        self.config("remote.origin.url", self.bare)         # the remote git uses for a branch with no upstream
        self.unresolved("origin")
        self.real_fails("origin")

    def test_simple_to_another_remote_than_the_default_is_current(self):
        self.assertEqual(["refs/heads/feature:refs/heads/feature"], self.agree("local")["push_updates"])

    def test_simple_needs_the_upstream_to_be_on_this_remote(self):
        self.bare_remote("second.git", "second")
        self.upstream(remote="second")
        self.assertEqual(["refs/heads/feature:refs/heads/feature"], self.agree("local")["push_updates"])    # triangular
        self.upstream(remote="local")
        self.assertEqual(["refs/heads/feature:refs/heads/feature"], self.agree("local")["push_updates"])

    def test_upstream_pushes_to_the_branch_the_upstream_names(self):
        self.config("push.default", "upstream")
        self.upstream(merge="refs/heads/" + self.main)
        self.assertEqual(["refs/heads/feature:refs/heads/" + self.main], self.agree("local")["push_updates"])

    def test_tracking_is_the_old_name_of_upstream(self):
        self.config("push.default", "tracking")
        self.upstream(merge="refs/heads/" + self.main)
        self.assertEqual(["refs/heads/feature:refs/heads/" + self.main], self.agree("local")["push_updates"])

    def test_upstream_without_an_upstream_is_unresolved(self):
        self.config("push.default", "upstream")
        self.unresolved("local")
        self.real_fails("local")

    def test_upstream_with_two_merge_lines_is_unresolved(self):
        self.config("push.default", "upstream")
        self.upstream()
        self.add("branch.feature.merge", "refs/heads/" + self.main)
        self.unresolved("local")

    def test_upstream_on_another_remote_is_unresolved(self):
        self.bare_remote("second.git", "second")
        self.config("push.default", "upstream")
        self.upstream(remote="second")
        self.unresolved("local")
        self.real_fails("local")

    def test_a_merge_that_is_not_a_branch_or_tag_is_unresolved(self):
        self.config("push.default", "upstream")
        self.upstream(merge="feature")
        self.unresolved("local")

    def test_nothing_is_unresolved(self):
        self.config("push.default", "nothing")
        self.unresolved("local")
        self.real_fails("local")

    def test_matching_needs_the_remote(self):
        self.config("push.default", "matching")
        self.unresolved("local", code="remote_state_required")

    def test_a_value_git_refuses_is_a_repository_git_cannot_read(self):
        for value in ("bogus", "Simple", ""):
            with self.subTest(value=value):
                self.config("push.default", value)
                self.unresolved("local", code="repository_unreadable")
        self.real_fails("local")

    def test_a_push_default_with_no_value_is_a_repository_git_cannot_read(self):
        with open(os.path.join(self.repo, ".git", "config"), "a") as handle:
            handle.write("[push]\n\tdefault\n")
        self.unresolved("local", code="repository_unreadable")

    def test_the_last_push_default_wins(self):
        self.config("push.default", "nothing")
        self.add("push.default", "current")
        self.assertEqual(["refs/heads/feature:refs/heads/feature"], self.agree("local")["push_updates"])

    def test_a_push_remote_makes_simple_act_as_current(self):
        self.bare_remote("fork.git", "fork")
        self.upstream(remote="local")
        self.config("branch.feature.pushRemote", "fork")
        facts = self.agree()
        self.assertEqual(("fork", ["refs/heads/feature:refs/heads/feature"]), (facts["remote"], facts["push_updates"]))
        self.assertEqual(["refs/heads/feature:refs/heads/feature"], self.agree("fork")["push_updates"])
        self.assertEqual(["refs/heads/feature:refs/heads/feature"], self.agree("local")["push_updates"])

    def test_a_push_remote_makes_upstream_unresolved(self):
        self.bare_remote("fork.git", "fork")
        self.config("push.default", "upstream")
        self.upstream(remote="local")
        self.config("branch.feature.pushRemote", "fork")
        self.unresolved()
        self.real_fails()

    def test_the_remote_of_the_branch_must_be_a_name(self):
        self.upstream(remote="")
        self.unresolved("local")


class ConfiguredPush(Target):
    def setUp(self):
        super().setUp()
        self.unset("push.default")
        self.commit("b.txt", "two\n")

    def test_one_refspec_is_what_the_push_asks_for(self):
        for value, expected in (("refs/heads/feature:refs/heads/viaconfig", "refs/heads/feature:refs/heads/viaconfig"),
                                ("HEAD:viaconfig2", "HEAD:refs/heads/viaconfig2"),
                                ("feature", "refs/heads/feature:refs/heads/feature"),
                                ("+feature:viaconfig3", "refs/heads/feature:refs/heads/viaconfig3")):
            with self.subTest(value=value):
                self.config("remote.local.push", value)
                facts = self.agree("local")
                self.assertEqual([expected], facts["push_updates"])
        self.assertEqual(["refs/heads/viaconfig3"], facts["push_forced"])

    def test_head_is_the_current_branch_there_too(self):
        self.config("remote.local.push", "HEAD")
        self.assertEqual(["HEAD:refs/heads/feature"], self.agree("local")["push_updates"])

    def test_a_deletion_by_a_full_ref_is_read(self):
        self.create("gone")
        self.config("remote.local.push", ":refs/heads/gone")
        facts = self.agree("local")
        self.assertEqual((["refs/heads/gone"], []), (facts["push_deletes"], facts["push_updates"]))

    def test_a_bare_deletion_is_unresolved(self):
        self.config("remote.local.push", ":gone")
        self.unresolved("local")

    def test_an_argument_refspec_beats_the_configuration(self):
        self.config("remote.local.push", "refs/heads/feature:refs/heads/viaconfig")
        self.assertEqual(["refs/heads/feature:refs/heads/mine"], self.agree("local", "feature:mine")["push_updates"])

    def test_the_configuration_beats_push_default(self):
        self.config("push.default", "nothing")
        self.config("remote.local.push", "feature:viaconfig")
        self.assertEqual(["refs/heads/feature:refs/heads/viaconfig"], self.agree("local")["push_updates"])

    def test_the_configuration_of_another_remote_is_not_read(self):
        self.bare_remote("fork.git", "fork")
        self.config("remote.fork.push", "feature:onfork")
        self.config("push.default", "current")
        self.assertEqual(["refs/heads/feature:refs/heads/feature"], self.agree("local")["push_updates"])

    def test_two_refspecs_are_unresolved(self):
        self.config("remote.local.push", "feature:a")
        self.add("remote.local.push", "feature:b")
        self.unresolved("local")
        self.assertEqual(2, len(self.real("local")[0]))

    def test_a_source_other_than_the_current_branch_is_unresolved(self):
        self.config("remote.local.push", self.main + ":" + self.main)
        self.unresolved("local")

    def test_a_wildcard_needs_the_remote(self):
        self.config("remote.local.push", "refs/heads/*:refs/heads/*")
        self.unresolved("local", code="remote_state_required")

    def test_an_odd_refspec_is_unresolved(self):
        for value in ("^feature", "-x", "feature:a:b"):
            with self.subTest(value=value):
                self.config("remote.local.push", value)
                self.unresolved("local")

    def test_a_refspec_git_refuses_is_a_repository_git_cannot_read(self):
        for value in ("", "+"):
            with self.subTest(value=value):
                self.config("remote.local.push", value)
                self.unresolved("local", code="repository_unreadable")

    def test_a_refspec_with_no_value_is_a_repository_git_cannot_read(self):
        with open(os.path.join(self.repo, ".git", "config"), "a") as handle:
            handle.write('[remote "local"]\n\tpush\n')
        self.unresolved("local", code="repository_unreadable")

    def test_no_message_quotes_the_refspec(self):
        token = "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0" * 2
        self.config("remote.local.push", "feature:" + token + ":x")
        self.assertNotIn(token, self.unresolved("local")["errors"][0]["message"])


class RemoteState(Target):
    def test_follow_tags_needs_the_remote(self):
        for value in ("true", "yes", "1", "on"):
            with self.subTest(value=value):
                self.config("push.followTags", value)
                self.unresolved("local", code="remote_state_required")
                self.unresolved("local", "feature", code="remote_state_required")

    def test_follow_tags_with_no_value_is_true(self):
        with open(os.path.join(self.repo, ".git", "config"), "a") as handle:
            handle.write("[push]\n\tfollowTags\n")
        self.unresolved("local", code="remote_state_required")

    def test_follow_tags_off_is_not_a_refusal(self):
        for value in ("false", "no", "0", "off"):
            with self.subTest(value=value):
                self.config("push.followTags", value)
                self.assertTrue(self.describe("local", "feature")["ok"])

    def test_the_last_follow_tags_wins(self):
        self.config("push.followTags", "true")
        self.add("push.followTags", "false")
        self.assertTrue(self.describe("local", "feature")["ok"])
        self.add("push.followTags", "true")
        self.unresolved("local", "feature", code="remote_state_required")

    def test_follow_tags_of_the_owner_counts_too(self):
        self.global_config("[push]\n\tfollowTags = true\n")
        self.unresolved("local", "feature", code="remote_state_required")

    def test_a_mirror_remote_needs_the_remote(self):
        self.config("remote.local.mirror", "true")
        self.unresolved("local", "feature", code="remote_state_required")
        self.unresolved("local", code="remote_state_required")

    def test_the_mirror_setting_of_another_remote_is_not_this_remote(self):
        self.bare_remote("fork.git", "fork")
        self.config("remote.fork.mirror", "true")
        self.assertTrue(self.describe("local", "feature")["ok"])
        self.config("remote.local.mirror", "false")
        self.assertTrue(self.describe("local", "feature")["ok"])

    def test_two_push_urls_are_refused(self):
        self.config("remote.local.pushurl", self.bare)
        self.add("remote.local.pushurl", self.bare + "-other")
        self.unresolved("local", "feature", code="multiple_push_urls")


class Base(Target):
    """The base of the range follows the destination (spec: "The range")."""

    def test_the_base_is_the_tracking_ref_of_the_destination_branch(self):
        middle = self.commit("b.txt", "two\n")
        self.commit("c.txt", "three\n")
        git(self.repo, "update-ref", "refs/remotes/local/other", middle)
        facts = self.describe("local", "HEAD:other")["facts"]
        self.assertEqual((middle, 1), (facts["base"], facts["ahead"]))

    def test_a_new_destination_is_compared_with_the_default_branch(self):
        self.commit("b.txt", "two\n")
        facts = self.describe("local", "HEAD:brandnew")["facts"]
        self.assertEqual((self.first, 1), (facts["base"], facts["ahead"]))

    def test_a_tag_destination_is_compared_with_the_default_branch(self):
        middle = self.commit("b.txt", "two\n")
        git(self.repo, "update-ref", "refs/remotes/local/feature", middle)
        self.commit("c.txt", "three\n")
        facts = self.describe("local", "HEAD:refs/tags/v1")["facts"]
        self.assertEqual(self.first, facts["base"])

    def test_the_branch_name_is_not_the_destination(self):
        middle = self.commit("b.txt", "two\n")
        git(self.repo, "update-ref", "refs/remotes/local/feature", middle)
        self.commit("c.txt", "three\n")
        facts = self.describe("local", "HEAD:elsewhere")["facts"]
        self.assertEqual(self.first, facts["base"])

    def test_a_destination_with_no_base_is_unresolved(self):
        git(self.repo, "symbolic-ref", "--delete", "refs/remotes/local/HEAD")
        self.refused("base_unresolved", "local", "HEAD:brandnew")

    def test_a_tag_destination_without_a_default_branch_is_base_unresolved(self):
        git(self.repo, "symbolic-ref", "--delete", "refs/remotes/local/HEAD")
        built = self.refused("base_unresolved", "local", "HEAD:refs/tags/v1")
        self.assertEqual(["refs/tags/v1"], [item.partition(":")[2] for item in built["facts"]["push_updates"]])


class Shapes(unittest.TestCase):
    def test_a_tag_ref_can_be_read(self):
        for ref in ("refs/tags/v1", "refs/tags/a/b", "refs/heads/x", "refs/remotes/origin/x"):
            self.assertTrue(H.git_shape_ok(["git", "show-ref", "--verify", "--hash", ref]), ref)

    def test_other_refs_cannot(self):
        for ref in ("refs/tags/", "refs/tags/../x", "refs/tags/x.lock", "refs/tags/.x", "refs/notes/x", "refs/tags/x/",
                    "refs/tags//x", "refs/tags/x@{1}", "refs/tags/-x", "refs/stash", "tags/x", "HEAD", "-x"):
            self.assertFalse(H.git_shape_ok(["git", "show-ref", "--verify", "--hash", ref]), ref)


if __name__ == "__main__":
    unittest.main()
