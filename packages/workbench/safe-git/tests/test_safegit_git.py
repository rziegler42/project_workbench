"""The helper's git runner and the repository checks (plan `2026-10-22-code-work-commit`, increment A).

Real git, real repositories and a `git` that records how it is run. Nothing here runs a subcommand of
the helper; that is increment B on. The contract tested is written out in the plan, under "The contract
ported", so these tests do not read the owner's private script."""

import os
import tempfile
import unittest
import unittest.mock

from tests import support_helpers

import support_git
from support_git import git, needs_git

H = support_helpers.load("safe-git")
STANDARD = "/usr/bin" + os.pathsep + "/bin"


def environment(*front, **more):
    """A caller environment whose PATH is `front` entries then the standard ones."""
    env = {"PATH": os.pathsep.join(list(front) + [STANDARD]), "HOME": tempfile.gettempdir()}
    env.update(more)
    return env


@needs_git
class Path(support_git.Repo):
    def test_only_absolute_entries_outside_the_repository_are_trusted(self):
        inside = os.path.join(self.repo, "bin")
        os.mkdir(inside)
        link = os.path.join(self.scratch, "alias")
        os.symlink(inside, link)
        entries = ["", ".", "relative/dir", inside, link, self.outside, "/usr/bin"]
        with unittest.mock.patch.dict(os.environ, {"PATH": os.pathsep.join(entries)}):
            self.assertEqual([self.outside, "/usr/bin"], H.trusted_path_entries(self.repo))

    def test_a_missing_entry_inside_the_repository_is_never_trusted(self):
        """A directory that does not exist yet is inside when what it would be made in is: a program put there
        later would otherwise be found."""
        missing = os.path.join(self.repo, "missing-bin")
        deeper = os.path.join(self.repo, "a", "b", "c")
        with unittest.mock.patch.dict(os.environ, {"PATH": os.pathsep.join([missing, deeper, self.outside])}):
            self.assertEqual([self.outside], H.trusted_path_entries(self.repo))

    def test_containment_fails_closed(self):
        self.assertTrue(H.is_inside(os.path.join(self.repo, "missing", "deeper"), self.repo))
        self.assertTrue(H.is_inside(self.repo, self.repo))
        self.assertFalse(H.is_inside(os.path.join(self.scratch, "missing"), self.repo))
        self.assertFalse(H.is_inside(self.outside, self.repo))
        with unittest.mock.patch.object(H.os.path, "samefile", side_effect=PermissionError):
            self.assertTrue(H.is_inside(self.outside, self.repo))

    def test_a_git_inside_the_repository_is_never_the_one_that_runs(self):
        inside = os.path.join(self.repo, "bin")
        os.mkdir(inside)
        marker = os.path.join(self.scratch, "ran-from-repo")
        with open(os.path.join(inside, "git"), "w") as handle:
            handle.write("#!/bin/sh\ntouch '%s'\n" % marker)
        os.chmod(os.path.join(inside, "git"), 0o755)
        self.recording_git()
        with unittest.mock.patch.dict(os.environ, environment(inside, "relative", "", self.outside), clear=True):
            H.run(["git", "rev-parse", "HEAD"], self.repo)
        self.assertFalse(os.path.exists(marker))
        self.assertEqual(1, len(self.runs()))

    def test_a_symbolic_link_to_a_git_in_the_repository_is_not_trusted(self):
        inside = os.path.join(self.repo, "bin")
        os.mkdir(inside)
        marker = os.path.join(self.scratch, "ran-through-link")
        with open(os.path.join(inside, "real"), "w") as handle:
            handle.write("#!/bin/sh\ntouch '%s'\n" % marker)
        os.chmod(os.path.join(inside, "real"), 0o755)
        linked = os.path.join(self.scratch, "linked")
        os.mkdir(linked)
        os.symlink(os.path.join(inside, "real"), os.path.join(linked, "git"))
        with unittest.mock.patch.dict(os.environ, {"PATH": linked}, clear=True):
            self.assertIsNone(H.trusted_which("git", self.repo))

    def test_with_no_git_outside_the_repository_the_run_is_refused(self):
        with unittest.mock.patch.dict(os.environ, {"PATH": os.path.join(self.repo, "nothing")}, clear=True):
            with unittest.mock.patch.object(H, "FALLBACK_PATH", [self.scratch]):
                with self.assertRaises(H.Refused):
                    H.run(["git", "rev-parse", "HEAD"], self.repo)


@needs_git
class Nested(support_git.Repo):
    """A nested repository's own configuration runs a program the top repository never names."""

    def setUp(self):
        super().setUp()
        self.marker = os.path.join(self.scratch, "nested-ran")
        script = os.path.join(self.scratch, "mon.sh")
        with open(script, "w") as handle:
            handle.write("#!/bin/sh\ntouch '%s'\nexit 1\n" % self.marker)
        os.chmod(script, 0o755)
        self.script = script
        patcher = unittest.mock.patch.dict(os.environ, environment("/usr/bin", HOME=self.scratch), clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def submodule(self, committed=True):
        sub = os.path.join(self.repo, "sub")
        os.mkdir(sub)
        git(sub, "init", "-q")
        with open(os.path.join(sub, "f.txt"), "w") as handle:
            handle.write("x\n")
        with open(os.path.join(sub, ".gitattributes"), "w") as handle:
            handle.write("f.txt filter=x\n")
        git(sub, "add", "f.txt", ".gitattributes")
        git(sub, "commit", "-q", "-m", "inner")
        if committed:
            git(self.repo, "add", "sub")
            git(self.repo, "commit", "-q", "-m", "gitlink")
        git(sub, "config", "filter.x.clean", self.script)
        later = os.stat(os.path.join(sub, "f.txt")).st_mtime + 100
        os.utime(os.path.join(sub, "f.txt"), (later, later))   # looks changed, so git runs the clean filter
        return sub

    def test_a_committed_gitlink_is_a_finding_so_the_commit_is_refused(self):
        self.submodule()
        self.assertEqual(["submodule:sub"], H.repo_program_findings(self.repo))

    def test_the_nested_program_does_run_without_the_finding(self):
        """Why the finding exists: these shapes start the inner repository's program."""
        self.submodule()
        H.run(["git", "diff", "--name-only", "-z"], self.repo, check=False)
        self.assertTrue(os.path.exists(self.marker))

    def test_an_untracked_nested_repository_is_not_a_finding_and_runs_nothing(self):
        self.submodule(committed=False)
        self.assertEqual([], H.repo_program_findings(self.repo))
        for argv in (["diff", "--name-only", "-z"], ["status", "--porcelain=v1", "-z", "--untracked-files=all"]):
            H.run(["git", *argv], self.repo, check=False)
        self.assertFalse(os.path.exists(self.marker))

    def test_many_gitlinks_are_reported_without_a_flood(self):
        for number in range(40):
            sub = os.path.join(self.repo, "s%02d" % number)
            os.mkdir(sub)
            git(sub, "init", "-q")
            with open(os.path.join(sub, "f"), "w") as handle:
                handle.write("x")
            git(sub, "add", "f")
            git(sub, "commit", "-q", "-m", "i")
            git(self.repo, "add", os.path.basename(sub))
        git(self.repo, "commit", "-q", "-m", "many")
        found = H.repo_program_findings(self.repo)
        self.assertEqual(H.MAX_GITLINK_FINDINGS, len(found))
        self.assertTrue(all(each.startswith("submodule:") for each in found))


@needs_git
class Boundary(support_git.Repo):
    def test_a_path_entry_in_the_outer_repository_is_not_trusted_from_an_embedded_one(self):
        outer_bin = os.path.join(self.repo, "bin")
        os.mkdir(outer_bin)
        marker = os.path.join(self.scratch, "ran-from-outer")
        with open(os.path.join(outer_bin, "git"), "w") as handle:
            handle.write("#!/bin/sh\ntouch '%s'\n" % marker)
        os.chmod(os.path.join(outer_bin, "git"), 0o755)
        inner = os.path.join(self.repo, "sub")
        os.mkdir(inner)
        git(inner, "init", "-q")
        with unittest.mock.patch.dict(os.environ, environment(outer_bin), clear=True):
            H.run(["git", "rev-parse", "--show-toplevel"], inner)
        self.assertFalse(os.path.exists(marker))

    def test_the_outermost_repository_is_the_boundary_and_the_nearest_is_the_root(self):
        inner = os.path.join(self.repo, "sub")
        os.mkdir(inner)
        git(inner, "init", "-q")
        deeper = os.path.join(inner, "d")
        os.mkdir(deeper)
        self.assertEqual(self.repo, H.outermost_boundary(deeper))
        self.assertEqual(inner, H.repository_boundary(deeper))


class Shapes(unittest.TestCase):
    def test_a_path_that_leaves_the_repository_is_refused_in_every_shape_that_takes_paths(self):
        for path in ("/etc/passwd", "../x", "a/../../x", "..", "a/..", ""):
            with self.subTest(path=path):
                for argv in (["diff", "--check", "--", path], ["diff", "--name-only", "-z", "--", "a.txt", path],
                             ["ls-files", "--error-unmatch", "--", path], ["ls-files", "-s", "-z", "--", path],
                             ["add", "--", path], ["reset", "-q", "--", path],
                             ["commit", "-m", "s", "--only", "--", path]):
                    self.assertFalse(H.git_shape_ok(["git", *argv]), argv)

    def test_a_path_inside_the_repository_is_accepted(self):
        for path in ("a.txt", "dir/sub/b.txt", "a b.txt", "-dash.txt", "dot..name", ".hidden"):
            self.assertTrue(H.git_shape_ok(["git", "add", "--", path]), path)

    def test_the_index_listing_without_paths_is_a_shape(self):
        self.assertTrue(H.git_shape_ok(["git", "ls-files", "-s", "-z"]))

    def test_the_refusal_names_a_command_in_a_bounded_message(self):
        with self.assertRaises(H.Refused) as caught:
            H.run(["git", "push", "x" * 5000000], os.getcwd())
        self.assertLess(len(str(caught.exception)), 400)


@needs_git
class Environment(support_git.Repo):
    HOSTILE = {
        "GIT_DIR": "/nonexistent", "GIT_WORK_TREE": "/nonexistent", "GIT_INDEX_FILE": "/nonexistent",
        "GIT_OBJECT_DIRECTORY": "/nonexistent", "GIT_CONFIG_COUNT": "5", "GIT_CONFIG_KEY_0": "core.sshcommand",
        "GIT_CONFIG_VALUE_0": "/bin/false", "GIT_CONFIG_PARAMETERS": "'core.fsmonitor=/bin/false'",
        "GIT_EXEC_PATH": "/nonexistent", "GIT_SSH_COMMAND": "/bin/false", "GIT_ASKPASS": "/bin/false",
        "GIT_EDITOR": "/bin/false", "GIT_PAGER": "/bin/false", "GIT_EXTERNAL_DIFF": "/bin/false",
        "GIT_TRACE": "1", "GIT_REPLACE_REF_BASE": "refs/x/", "GIT_NO_REPLACE_OBJECTS": "0",
        "GIT_TERMINAL_PROMPT": "1", "GIT_LITERAL_PATHSPECS": "0", "GIT_CEILING_DIRECTORIES": "/",
        "EDITOR": "/bin/false", "VISUAL": "/bin/false", "PAGER": "/bin/false", "SSH_ASKPASS": "/bin/false",
        "SECRET_TOKEN": "hunter2", "LD_PRELOAD": "/nonexistent", "DYLD_INSERT_LIBRARIES": "/nonexistent",
    }

    def logged_environment(self):
        self.recording_git()
        with unittest.mock.patch.dict(os.environ, environment(self.outside, LC_ALL="C", LANG="C",
                                                              **self.HOSTILE), clear=True):
            H.run(["git", "rev-parse", "HEAD"], self.repo)
        [(arguments, seen)] = self.runs()
        return seen

    def test_no_git_variable_of_the_caller_and_nothing_else_unkept_reaches_git(self):
        seen = self.logged_environment()
        for name, value in self.HOSTILE.items():
            self.assertNotEqual(value, seen.get(name), name)
        self.assertNotIn("SECRET_TOKEN", seen)
        self.assertNotIn("LD_PRELOAD", seen)
        self.assertNotIn("DYLD_INSERT_LIBRARIES", seen)
        self.assertNotIn("GIT_DIR", seen)

    def test_the_helper_sets_the_few_variables_it_needs(self):
        seen = self.logged_environment()
        self.assertEqual("1", seen["GIT_NO_REPLACE_OBJECTS"])
        self.assertEqual("0", seen["GIT_TERMINAL_PROMPT"])
        self.assertEqual("true", seen["GIT_EDITOR"])
        self.assertEqual("cat", seen["GIT_PAGER"])
        self.assertEqual("1", seen["GIT_LITERAL_PATHSPECS"])
        self.assertEqual("1", seen["GIT_NO_LAZY_FETCH"])

    def test_the_helper_switches_the_file_system_monitor_off_for_every_run(self):
        seen = self.logged_environment()
        self.assertEqual("false", seen["GIT_CONFIG_VALUE_0"])
        self.assertEqual("core.fsmonitor", seen["GIT_CONFIG_KEY_0"])
        count = int(seen["GIT_CONFIG_COUNT"])
        settings = {seen["GIT_CONFIG_KEY_%d" % n]: seen["GIT_CONFIG_VALUE_%d" % n] for n in range(count)}
        self.assertEqual("false", settings["maintenance.auto"])   # no automatic maintenance after a commit
        self.assertEqual("0", settings["gc.auto"])
        self.assertNotIn("GIT_CONFIG_PARAMETERS", seen)

    def test_the_locale_and_the_home_of_the_caller_are_kept(self):
        seen = self.logged_environment()
        self.assertEqual("C", seen["LC_ALL"])
        self.assertEqual(tempfile.gettempdir(), seen["HOME"])

    def test_path_is_only_the_trusted_entries(self):
        seen = self.logged_environment()
        entries = seen["PATH"].split(os.pathsep)
        self.assertEqual(self.outside, entries[0])
        self.assertTrue(all(os.path.isabs(each) for each in entries))

    def test_a_repository_cannot_choose_the_editor_or_pager_for_a_run(self):
        self.config("core.editor", "/bin/false")
        self.config("core.pager", "/bin/false")
        self.recording_git()
        with unittest.mock.patch.dict(os.environ, environment(self.outside), clear=True):
            result = H.run(["git", "show", "-s", "--format=%s", "HEAD"], self.repo)
        self.assertEqual("first", result.stdout.strip())


@needs_git
class Allowed(support_git.Repo):
    """Only the git subcommands the plan lists, each in the one shape the helper uses."""

    def setUp(self):
        super().setUp()
        self.recording_git()
        patcher = unittest.mock.patch.dict(os.environ, environment(self.outside), clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def refused(self, *argv):
        with self.assertRaises(H.Refused):
            H.run(["git", *argv], self.repo)
        self.assertEqual([], self.runs(), argv)

    def test_the_commands_that_move_or_publish_history_are_refused(self):
        for argv in (["push"], ["fetch"], ["pull"], ["checkout", "a.txt"], ["switch", "-"], ["merge", "HEAD"],
                     ["rebase", "HEAD"], ["tag", "x"], ["branch", "x"], ["stash"], ["clean", "-fd"],
                     ["restore", "a.txt"], ["rm", "a.txt"], ["mv", "a", "b"], ["gc"], ["remote", "add", "x", "y"],
                     ["update-ref", "HEAD", "HEAD"], ["cherry-pick", "HEAD"], ["revert", "HEAD"],
                     ["am"], ["apply"], ["filter-branch"], ["worktree", "add", "x"], ["submodule", "update"]):
            self.refused(*argv)

    def test_a_global_option_before_the_subcommand_is_refused(self):
        for argv in (["-c", "core.fsmonitor=/bin/false", "status"], ["--exec-path=/tmp", "status"],
                     ["-C", "/", "status"], ["--git-dir=/x", "status"], ["--work-tree=/x", "status"],
                     ["--no-pager", "status"], ["--namespace=x", "status"], [""], []):
            self.refused(*argv)

    def test_reset_is_only_the_unstage_of_named_paths(self):
        for argv in (["reset", "--hard"], ["reset", "--hard", "HEAD"], ["reset", "HEAD"], ["reset", "-q"],
                     ["reset", "-q", "--"], ["reset", "--soft", "HEAD~1"], ["reset", "-q", "HEAD", "--", "a.txt"],
                     ["reset", "--mixed", "--", "a.txt"], ["reset", "-q", "a.txt"]):
            self.refused(*argv)
        H.run(["git", "reset", "-q", "--", "a.txt"], self.repo)
        self.assertEqual(1, len(self.runs()))

    def test_commit_takes_messages_and_only_named_paths_and_nothing_else(self):
        for argv in (["commit", "--amend", "-m", "x"], ["commit", "-m", "x", "--amend"], ["commit", "-a", "-m", "x"],
                     ["commit", "-m"], ["commit"], ["commit", "--no-verify", "-m", "x"],
                     ["commit", "-m", "x", "--only"], ["commit", "-m", "x", "--only", "--"],
                     ["commit", "-m", "x", "--", "a.txt"], ["commit", "-F", "/etc/passwd"],
                     ["commit", "-m", "x", "-C", "HEAD"], ["commit", "--allow-empty", "-m", "x"]):
            self.refused(*argv)

    def test_add_diff_and_ls_files_take_paths_only_after_a_double_dash(self):
        for argv in (["add", "a.txt"], ["add", "-A"], ["add", "--", ], ["add", "-f", "--", "a.txt"],
                     ["diff", "--ext-diff"], ["diff", "--output=/tmp/x"], ["diff", "--cached", "a.txt"],
                     ["diff", "--no-index", "--", "a", "b"], ["diff", "--cached", "--", ],
                     ["ls-files", "--others"], ["ls-files", "a.txt"], ["ls-files", "--error-unmatch", "a.txt"],
                     ["show", "HEAD"], ["show", "-s", "--format=%s", "--textconv", "HEAD"],
                     ["show", "-s", "--format=%H", "HEAD"], ["diff-tree", "HEAD"], ["config", "user.name", "x"],
                     ["config", "--global", "--list"], ["config", "--list"], ["status"],
                     ["rev-parse", "--git-dir"], ["rev-parse", "--local-env-vars"], ["rev-parse", "-q"]):
            self.refused(*argv)

    def test_a_diff_that_reads_file_contents_must_switch_off_external_programs(self):
        for argv in (["diff", "--check", "--", "a.txt"], ["diff", "--cached", "--check"],
                     ["diff", "--check", "--no-ext-diff", "--", "a.txt"],
                     ["diff", "--check", "--no-textconv", "--", "a.txt"]):
            self.refused(*argv)

    def test_the_shapes_the_helper_uses_are_accepted(self):
        for argv in (["rev-parse", "--show-toplevel"], ["rev-parse", "--absolute-git-dir"],
                     ["rev-parse", "--git-common-dir"], ["rev-parse", "HEAD"], ["rev-parse", "--verify", "HEAD"],
                     ["rev-parse", "HEAD^@"], ["rev-parse", "--verify", "-q", "refs/heads/main"],
                     ["diff", "--cached", "--name-only", "-z"], ["diff", "--name-only", "-z"],
                     ["diff", "--check", "--no-ext-diff", "--no-textconv", "--", "a.txt"],
                     ["diff", "--cached", "--check", "--no-ext-diff", "--no-textconv"],
                     ["ls-files", "--error-unmatch", "--", "a.txt"], ["ls-files", "-s", "-z", "--", "a.txt"],
                     ["add", "--", "a.txt"], ["show", "-s", "--format=%s", "HEAD"],
                     ["show", "-s", "--format=%B", "HEAD"],
                     ["diff-tree", "--no-commit-id", "--name-only", "-r", "-z", "HEAD"],
                     ["diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "-z", "HEAD"],
                     ["config", "--list", "-z"], ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
                     ["commit", "-m", "subject", "-m", "body"],
                     ["reset", "-q", "--", "a.txt"]):
            self.assertTrue(H.git_shape_ok(["git", *argv]), argv)
        self.assertTrue(H.git_shape_ok(["git", "commit", "-m", "s", "--only", "--", "a.txt"]))
        self.assertFalse(H.git_shape_ok(["svn", "status"]))
        self.assertFalse(H.git_shape_ok("git status"))

    def test_a_ref_that_is_not_a_plain_branch_name_is_refused_for_rev_parse(self):
        for ref in ("refs/heads/../x", "refs/heads/-x", "refs/remotes/o/x", "HEAD", "-q", "refs/heads/",
                    "refs/heads/a b", "refs/heads/a\nb", "refs/heads/" + "a" * 300):
            self.assertFalse(H.git_shape_ok(["git", "rev-parse", "--verify", "-q", ref]), ref)


@needs_git
class Root(support_git.Repo):
    def setUp(self):
        super().setUp()
        patcher = unittest.mock.patch.dict(os.environ, environment("/usr/bin"), clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_repository_and_a_directory_below_it_give_the_root(self):
        sub = os.path.join(self.repo, "docs", "plans")
        os.makedirs(sub)
        self.assertEqual(self.repo, H.git_root(self.repo))
        self.assertEqual(self.repo, H.git_root(sub))

    def test_head_and_the_staged_names(self):
        first = H.head(self.repo)
        self.assertEqual(40, len(first))
        self.assertEqual(set(), H.names(self.repo, cached=True))
        self.write("b.txt", "two\n")
        git(self.repo, "add", "b.txt")
        self.assertEqual({"b.txt"}, H.names(self.repo, cached=True))
        self.write("a.txt", "changed\n")
        self.assertEqual({"a.txt"}, H.names(self.repo))

    def test_a_directory_that_is_not_in_a_repository_is_refused(self):
        with self.assertRaises(H.Refused):
            H.git_root(self.scratch)

    def test_a_work_tree_redirect_is_refused(self):
        other = os.path.join(self.scratch, "other")
        os.mkdir(other)
        self.config("core.worktree", other)
        with self.assertRaises(H.Refused):
            H.git_root(self.repo)

    def test_a_git_directory_that_is_a_link_to_another_repository_is_refused(self):
        elsewhere = os.path.join(self.scratch, "elsewhere")
        os.mkdir(elsewhere)
        git(elsewhere, "init", "-q")
        linked = os.path.join(self.scratch, "linked")
        os.mkdir(linked)
        os.symlink(os.path.join(elsewhere, ".git"), os.path.join(linked, ".git"))
        with self.assertRaises(H.Refused):
            H.git_root(linked)

    def test_a_git_file_that_points_to_a_git_directory_elsewhere_is_refused(self):
        separate = os.path.join(self.scratch, "separate")
        os.mkdir(separate)
        git(separate, "init", "-q", "--separate-git-dir", os.path.join(self.scratch, "gitdir"))
        with self.assertRaises(H.Refused):
            H.git_root(separate)

    def test_a_failing_git_command_names_the_command_and_cleans_the_text(self):
        with self.assertRaises(H.Refused) as caught:
            H.run(["git", "rev-parse", "HEAD"], self.scratch)
        self.assertIn("rev-parse", str(caught.exception))
        self.assertTrue(str(caught.exception).isascii())


@needs_git
class Findings(support_git.Repo):
    """Settings and hooks that would make a commit run a program."""

    def setUp(self):
        super().setUp()
        self.home = os.path.join(self.scratch, "home")
        os.mkdir(self.home)
        patcher = unittest.mock.patch.dict(os.environ, environment("/usr/bin", HOME=self.home), clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def found(self):
        return H.repo_program_findings(self.repo)

    def test_a_clean_repository_has_none(self):
        self.assertEqual([], self.found())

    def test_each_key_shape_the_contract_names_is_found(self):
        for key in ("core.fsmonitor", "core.hooksPath", "core.sshCommand", "filter.x.clean", "filter.x.smudge",
                    "filter.x.process", "diff.x.command", "diff.external", "diff.x.textconv", "gpg.program",
                    "gpg.ssh.program", "gpg.ssh.defaultKeyCommand", "merge.x.driver", "alias.x.cmd",
                    "credential.helper.program", "sequence.editor.command", "difftool.x.cmd"):
            with self.subTest(key=key):
                git(self.repo, "config", key, "something")
                self.assertIn(key.lower(), [f.lower() for f in self.found()])
                git(self.repo, "config", "--unset", key)
                self.assertEqual([], self.found())

    def test_signing_is_found_only_when_it_is_on(self):
        for value, expected in (("true", True), ("yes", True), ("on", True), ("1", True), ("2", True),
                                ("false", False), ("no", False), ("off", False), ("0", False)):
            with self.subTest(value=value):
                self.config("commit.gpgsign", value)
                self.assertEqual(["commit.gpgsign"] if expected else [], self.found())

    def test_a_signing_key_with_no_value_counts_as_on(self):
        with open(os.path.join(self.repo, ".git", "config"), "a") as handle:
            handle.write("[commit]\n\tgpgsign\n")
        self.assertEqual(["commit.gpgsign"], self.found())

    def test_a_program_key_in_an_included_file_is_found(self):
        included = os.path.join(self.scratch, "extra.cfg")
        with open(included, "w") as handle:
            handle.write("[core]\n\tfsmonitor = /bin/false\n")
        self.config("include.path", included)
        self.assertIn("core.fsmonitor", self.found())

    def test_a_conditional_include_is_followed(self):
        included = os.path.join(self.scratch, "cond.cfg")
        with open(included, "w") as handle:
            handle.write("[core]\n\tsshCommand = /bin/false\n")
        with open(os.path.join(self.repo, ".git", "config"), "a") as handle:
            handle.write('[includeIf "gitdir:%s/"]\n\tpath = %s\n' % (self.repo, included))
        self.assertIn("core.sshcommand", [f.lower() for f in self.found()])

    def test_the_owners_global_configuration_is_trusted(self):
        with open(os.path.join(self.home, ".gitconfig"), "w") as handle:
            handle.write("[core]\n\tsshCommand = /usr/bin/ssh\n[filter \"lfs\"]\n\tclean = git-lfs clean\n")
        self.assertEqual([], self.found())

    def test_an_executable_hook_is_found_and_a_sample_or_a_plain_file_is_not(self):
        hooks = os.path.join(self.repo, ".git", "hooks")
        os.makedirs(hooks, exist_ok=True)
        for name, mode in (("pre-commit.sample", 0o755), ("commit-msg", 0o644), ("post-commit", 0o755)):
            with open(os.path.join(hooks, name), "w") as handle:
                handle.write("#!/bin/sh\nexit 0\n")
            os.chmod(os.path.join(hooks, name), mode)
        self.assertEqual(["hook:post-commit"], self.found())

    def test_the_names_are_reported_and_never_the_values(self):
        self.config("core.fsmonitor", "/secret/location/of/a/program")
        self.assertNotIn("secret", " ".join(self.found()))

    def test_a_configuration_that_cannot_be_read_is_a_finding(self):
        with open(os.path.join(self.repo, ".git", "config"), "w") as handle:
            handle.write("[core\n")
        self.assertEqual(["config:unreadable"], self.found())

    def program(self, name="prog.sh"):
        marker = os.path.join(self.scratch, name + ".ran")
        script = os.path.join(self.scratch, name)
        with open(script, "w") as handle:
            handle.write("#!/bin/sh\ntouch '%s'\nexit 1\n" % marker)
        os.chmod(script, 0o755)
        return script, marker

    def test_the_check_itself_never_runs_the_program_it_reports(self):
        script, marker = self.program()
        self.config("core.fsmonitor", script)
        self.assertEqual(["core.fsmonitor"], self.found())
        self.assertFalse(os.path.exists(marker))

    def test_a_file_system_monitor_set_to_false_is_not_a_finding(self):
        self.config("core.fsmonitor", "false")
        self.assertEqual([], self.found())

    def test_no_shape_the_helper_runs_starts_the_file_system_monitor(self):
        script, marker = self.program()
        self.config("core.fsmonitor", script)
        self.write("b.txt", "two\n")
        for argv in (["ls-files", "-s", "-z"], ["diff", "--name-only", "-z"], ["add", "--", "b.txt"],
                     ["diff", "--cached", "--name-only", "-z"], ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
                     ["commit", "-m", "s"], ["reset", "-q", "--", "b.txt"]):
            with self.subTest(argv=argv):
                H.run(["git", *argv], self.repo, check=False)
                self.assertFalse(os.path.exists(marker))

    def test_the_settings_that_make_git_fetch_or_ask_for_a_program_are_found(self):
        for key in ("extensions.partialClone", "remote.origin.promisor", "remote.origin.uploadpack",
                    "remote.origin.receivepack", "remote.origin.vcs", "remote.origin.partialCloneFilter",
                    "core.gitProxy", "core.askPass", "credential.helper", "credential.https://x.example.helper"):
            with self.subTest(key=key):
                git(self.repo, "config", key, "something")
                self.assertIn(key.lower(), [f.lower() for f in self.found()])
                git(self.repo, "config", "--unset", key)

    def test_a_missing_object_never_makes_a_diff_start_the_remote_program(self):
        script, marker = self.program()
        origin = os.path.join(self.scratch, "origin")
        os.mkdir(origin)
        git(origin, "init", "-q", "--bare")
        git(self.repo, "config", "core.repositoryformatversion", "1")
        for key, value in (("extensions.partialClone", "origin"), ("remote.origin.promisor", "true"),
                           ("remote.origin.url", origin), ("remote.origin.uploadpack", script)):
            git(self.repo, "config", key, value)
        blob = git(self.repo, "rev-parse", "HEAD:a.txt").stdout.strip()
        loose = os.path.join(self.repo, ".git", "objects", blob[:2], blob[2:])
        os.chmod(loose, 0o644)
        os.unlink(loose)
        self.write("a.txt", "changed\n")
        for argv in (["diff", "--check", "--no-ext-diff", "--no-textconv", "--", "a.txt"],
                     ["diff", "--cached", "--check", "--no-ext-diff", "--no-textconv"],
                     ["diff", "--name-only", "-z"], ["commit", "-m", "s"]):
            with self.subTest(argv=argv):
                H.run(["git", *argv], self.repo, check=False)
                self.assertFalse(os.path.exists(marker))

    def test_a_commit_never_starts_the_maintenance_program_a_repository_names(self):
        import hashlib
        script, marker = self.program()
        for key, value in (("gc.auto", "1"), ("gc.autoDetach", "false"), ("maintenance.strategy", "incremental"),
                           ("maintenance.loose-objects.auto", "1"), ("gc.recentObjectsHook", script)):
            git(self.repo, "config", key, value)
        for number in range(100000):      # loose objects git counts in its sample directory (names starting 17)
            data = b"filler %d\n" % number
            if hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest().startswith("17"):
                subprocess_input = data
                break
        import subprocess
        subprocess.run([support_git.REAL_GIT, "hash-object", "-w", "--stdin"], cwd=self.repo, input=subprocess_input,
                       env=dict(support_git._CLEAN, HOME=self.scratch), check=True, capture_output=True)
        self.write("b.txt", "two\n")
        git(self.repo, "add", "b.txt")
        H.run(["git", "commit", "-m", "s"], self.repo, check=False)
        self.assertFalse(os.path.exists(marker))

    def test_a_hooks_directory_that_cannot_be_listed_is_a_finding_and_not_skipped(self):
        script, marker = self.program()
        hooks = os.path.join(self.repo, ".git", "hooks")
        os.makedirs(hooks, exist_ok=True)
        os.symlink(script, os.path.join(hooks, "pre-commit"))
        for mode in (0o311, 0o111):
            with self.subTest(mode=oct(mode)):
                os.chmod(hooks, mode)
                self.addCleanup(os.chmod, hooks, 0o755)
                self.assertEqual(["hooks:unreadable"], self.found())

    def test_a_setting_whose_name_ends_in_hook_is_found(self):
        for key in ("gc.recentObjectsHook", "pack.packObjectsHook", "uploadpack.packObjectsHook"):
            with self.subTest(key=key):
                git(self.repo, "config", key, "something")
                self.assertIn(key.lower(), [f.lower() for f in self.found()])
                git(self.repo, "config", "--unset", key)

    def test_the_findings_are_sorted_and_without_repeats(self):
        self.config("core.fsmonitor", "x")
        self.config("filter.a.clean", "x")
        found = self.found()
        self.assertEqual(sorted(set(found)), found)


@needs_git
class ReadOnly(support_git.Repo):
    """The read-only subcommands still run no program: a recording git is never started."""

    def test_check_plans_and_report_do_not_start_git(self):
        self.recording_git()
        os.mkdir(os.path.join(self.repo, ".workbench"))
        with open(os.path.join(self.repo, ".workbench", "manifest.json"), "w") as handle:
            handle.write("{}\n")
        os.makedirs(os.path.join(self.repo, "docs", "plans"))
        import io
        with unittest.mock.patch.dict(os.environ, environment(self.outside), clear=True):
            for name in ("check", "plans", "report"):
                H.main([name], io.StringIO(), io.StringIO(), self.repo)
        self.assertEqual([], self.runs())


if __name__ == "__main__":
    unittest.main()
